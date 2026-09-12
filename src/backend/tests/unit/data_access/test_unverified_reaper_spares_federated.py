"""`cleanup_unverified_accounts` must not delete an account that can still sign in (#1403).

The task this query feeds HARD-DELETES what it returns, and `UserRepository.delete`
deliberately leaves memberships alone — the account-deletion cascade removes those
before calling it. So a row returned here in error costs the owner their account
and their personal tenant, and orphans the tenant's plant data.

`email_verified == false` alone was survivable only because nothing ever created a
federated account in that state: `_register_oauth_user` stamped `True`
unconditionally. #1403 made it read the provider's claim, and a provider that omits
`email_verified` — GitHub without the `user:email` scope, and many OIDC deployments
— then produces exactly such a row. The reaper would have deleted a working account
72 hours after its owner first signed in with it.

The AQL is checked statically, the way `test_lineage_aql_clause_order.py` checks the
traversal grammar: a mocked repository stubs `aql.execute` and never sends the string
anywhere that would notice. The behavioural half runs against a real ArangoDB in the
integration tier.
"""

from __future__ import annotations

import inspect
import re

from app.data_access.arango.user_repository import ArangoUserRepository


def _query_source() -> str:
    return inspect.getsource(ArangoUserRepository.get_unverified_before)


class TestTheReaperQueryExcludesFederatedAccounts:
    def test_it_consults_the_auth_provider_collection(self):
        source = _query_source()
        assert "@@providers" in source, (
            "get_unverified_before no longer looks at the auth-provider collection. Every account "
            "it returns is hard-deleted, so a federated account whose provider omits `email_verified` "
            "would be purged 72 hours after its owner signed in."
        )
        assert "col.AUTH_PROVIDERS" in source, "the @@providers bind variable is not bound to the collection"

    def test_it_filters_on_the_absence_of_a_provider(self):
        """Consulting the collection is not the same as acting on it."""
        source = _query_source()
        assert re.search(r"FILTER\s+linked\s*==\s*0", source), (
            "the provider lookup exists but nothing filters on its result — the subquery is computed "
            "and discarded, which reads like a guard and is not one"
        )

    def test_the_provider_lookup_is_keyed_on_the_user(self):
        source = _query_source()
        assert re.search(r"provider\.user_key\s*==\s*doc\._key", source), (
            "the subquery does not correlate the provider with the user under inspection; "
            "an uncorrelated LENGTH() would spare every account as soon as ANY provider row exists"
        )

    def test_the_unverified_and_cutoff_conditions_survive(self):
        """The control: a query that returns nothing is as wrong as one that returns everything."""
        source = _query_source()
        assert "doc.email_verified == false" in source
        assert "doc.created_at < @cutoff" in source
