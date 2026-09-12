from arango.database import StandardDatabase

from app.common.types import UserKey
from app.data_access.arango import collections as col
from app.data_access.arango.base_repository import BaseArangoRepository
from app.domain.interfaces.user_repository import IUserRepository
from app.domain.models.user import User


class ArangoUserRepository(BaseArangoRepository[User], IUserRepository):
    _model_cls = User

    def __init__(self, db: StandardDatabase) -> None:
        super().__init__(db, col.USERS)

    def update_fields(self, key: UserKey, fields: dict) -> User | None:
        """Merge ``fields`` into the stored user and rewrite it (#1018, mirrors #968 §2).

        Read-modify-write, exactly like :meth:`ArangoTenantRepository.update_fields`:
        the stored ``User`` is loaded, ``fields`` is applied through
        ``model_copy(update=...)`` and the merged model is written via the
        inherited full-model :meth:`update`, which re-validates it in ``_to_doc``
        (#982/#996), strips ArangoDB system attributes and maps a 1202 onto
        :class:`NotFoundError`. That is the set of guards the platform-admin
        router bypassed by writing ``collection.update`` itself (#1018).

        **Caller obligation.** ``fields`` is applied key-by-key, so it must be
        built from named fields or a validated schema's ``model_dump()`` — never
        from a raw request body.

        Deliberately not the base class's dict-merge :meth:`update_fields`, which
        writes the dict straight through unchecked; materialising a full ``User``
        here is what gets the payload validated. The price is that method's
        lost-update commutativity for disjoint concurrent fields.

        Returns ``None`` when no user carries ``key``.
        """
        existing = self.get_by_key(key)
        if not existing:
            return None
        merged = existing.model_copy(update=fields)
        return super().update(key, merged)

    def get_by_email(self, email: str) -> User | None:
        query = "FOR doc IN @@collection FILTER LOWER(doc.email) == LOWER(@email) LIMIT 1 RETURN doc"
        cursor = self._db.aql.execute(query, bind_vars={"@collection": col.USERS, "email": email})
        docs = list(cursor)
        if not docs:
            return None
        return User(**self._from_doc(docs[0]))

    def delete(self, key: UserKey) -> bool:
        """Delete a user and cascade every account-owned artefact (#1019).

        Auth-provider docs + edges, refresh tokens and session edges were already
        removed here; #1019 folded in the API keys, user preferences and
        onboarding state that the platform-admin ``delete_user`` router used to
        remove with its own raw AQL, so the full single-user purge now lives in
        one place. Memberships stay out of this method — they belong to the
        membership repository and are removed by the account-deletion cascade
        *before* this call (their per-tenant storage walk needs them alive).
        """
        user_id = f"{col.USERS}/{key}"
        # Delete auth provider edges + docs
        self.delete_edges(col.HAS_AUTH_PROVIDER, user_id)
        self._remove_docs_for_user(col.AUTH_PROVIDERS, key)
        # Delete refresh tokens
        self._remove_docs_for_user(col.REFRESH_TOKENS, key)
        # Delete session edges
        self.delete_edges(col.HAS_SESSION, user_id)
        # Delete API keys, preferences and onboarding state (#1019)
        self._remove_docs_for_user(col.API_KEYS, key)
        self._remove_docs_for_user(col.USER_PREFERENCES, key)
        self._remove_docs_for_user(col.ONBOARDING_STATES, key)
        return super().delete(key)

    def _remove_docs_for_user(self, collection: str, key: UserKey) -> None:
        """Remove every document in ``collection`` carrying ``user_key == key``.

        The collection name is always a ``collections.py`` code constant, so it
        is interpolated (never a caller value); ``key`` is bound.
        """
        query = f"FOR doc IN {collection} FILTER doc.user_key == @key REMOVE doc IN {collection}"
        self._db.aql.execute(query, bind_vars={"key": key})

    def list_all(self) -> list[User]:
        """Every user, newest first (platform-admin listing, #1019)."""
        docs = self._find_docs([], sort="created_at", sort_direction="DESC")
        return self._wrap_many(docs)

    def count(self, *, active_only: bool = False) -> int:
        """Number of user documents; ``active_only`` counts ``is_active`` ones (#1019)."""
        if not active_only:
            return self.collection.count()
        query = """
        FOR doc IN @@collection
          FILTER doc.is_active == true
          COLLECT WITH COUNT INTO cnt
          RETURN cnt
        """
        cursor = self._db.aql.execute(query, bind_vars={"@collection": col.USERS})
        return next(cursor, 0)

    def get_unverified_before(self, cutoff_iso: str) -> list[User]:
        """Abandoned half-registrations, for `cleanup_unverified_accounts` to purge.

        **An account with a linked federated provider is excluded, and that
        exclusion is load-bearing rather than tidy.** The task this feeds
        HARD-DELETES what it returns, and `delete` deliberately does not remove
        memberships — the account-deletion cascade does that before calling it.
        So a row returned here in error costs the user their account, their
        personal tenant, and leaves the tenant and its plant data orphaned.

        The predicate used to be `email_verified == false` alone. That was
        survivable only because nothing ever created a federated account in that
        state: `_register_oauth_user` stamped `email_verified=True`
        unconditionally. #1403 made it read the provider's claim instead, which is
        correct — and a provider that omits `email_verified` (GitHub without the
        `user:email` scope, and many OIDC deployments) then produces exactly such
        a row. The reaper would have deleted a working account 72 hours after its
        owner signed in with it.

        The distinction the task actually wants is "can this person still get in?",
        not "did they confirm an address". Someone who signs in through a provider
        can, today and every day after, so they are not an abandoned registration
        whatever `email_verified` says.
        """
        query = """
        FOR doc IN @@collection
          FILTER doc.email_verified == false AND doc.created_at < @cutoff
          LET linked = LENGTH(
            FOR provider IN @@providers
              FILTER provider.user_key == doc._key
              LIMIT 1
              RETURN 1
          )
          FILTER linked == 0
          RETURN doc
        """
        cursor = self._db.aql.execute(
            query,
            bind_vars={"@collection": col.USERS, "@providers": col.AUTH_PROVIDERS, "cutoff": cutoff_iso},
        )
        return [User(**self._from_doc(doc)) for doc in cursor]
