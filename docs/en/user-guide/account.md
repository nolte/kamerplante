<!-- REQ-023 — Source: src/frontend/src/pages/auth/{LoginPage,RegisterPage,EmailVerificationPage,PasswordResetRequestPage,PasswordResetConfirmPage,OAuthCallbackPage,AccountSettingsPage}.tsx, src/backend/app/domain/services/auth_service.py, src/backend/app/domain/engines/login_throttle_engine.py, src/backend/app/config/settings.py -->

# Account & Sign-In

This page explains how to create a Kamerplanter account, sign in, and manage your personal settings such as profile, language and active sessions.

!!! info "Applies to Full Mode"
    This page describes multi-user operation (Full Mode) with registration and login. If your instance runs in **Light Mode**, there is no sign-in at all — see [Light Mode](light-mode.md).

---

## Prerequisites

- Your Kamerplanter instance runs in Full Mode
- A valid email address you have access to

## Creating an Account (Registration)

1. Open the sign-in page and click **Don't have an account? Register**
2. Fill in the form:

    | Field | Description |
    |-------|-------------|
    | **Display Name** | Your name as shown in the app |
    | **Email** | Your sign-in email address |
    | **Password** | At least 10 characters |
    | **Confirm Password** | Must match the password |

3. Click **Register**

Registration automatically creates your **personal tenant** (see [Tenants & Gardens](tenants.md)) — your private space for plants, locations and tasks.

### Confirming Your Email Address

After registering, you receive an email with a confirmation link.

1. Open the email and click the confirmation link
2. The page shows **Email successfully verified** — you can now sign in
3. Click **Log in** to go straight to the sign-in page

!!! warning "Sign-in only works after confirmation"
    As long as your email address is unconfirmed, the system rejects sign-in attempts. The confirmation link is valid for **24 hours**. If the email doesn't arrive, check your spam folder.

#### When the Confirmation Link No Longer Works

If the link is older than 24 hours or was copied incompletely, the page shows a red notice instead of the success message — for example **Invalid or expired token**. Below it you will find the same **Log in** button, which takes you back to the sign-in page. From there you can sign in (if your address was already confirmed via an earlier link) or use **Forgot password?** to have another email sent to you.

!!! note "Changed behaviour"
    Up to this version this error page was a dead end: it showed only the error message and no way back into the application — you had to type the sign-in page's address yourself. <!-- REQ-023 -->

---

## Signing In

### With Email and Password

1. Enter your email address and password
2. Optionally enable **Remember me**
3. Click **Log in**

!!! tip "Only use \"Remember me\" on private devices"
    Without **Remember me**, your session expires after 24 hours. With it enabled, it stays active for up to 30 days. Only use this option on devices no one else can access.

### Signing In with Google, GitHub or Another Provider

If your administrator has configured external sign-in providers, additional buttons such as **Log in with Google** appear below the sign-in form. Under the hood, Kamerplanter uses **OpenID Connect (OIDC)**, an open standard that connects providers such as Google, GitHub or Apple.

1. Click the button for the provider you want to use
2. Sign in with the provider and confirm access
3. You are redirected back to Kamerplanter and signed in

Kamerplanter links the provider to an existing local account only when **both sides** confirm the email address: your local account and the provider. If sign-in fails, you land back on the sign-in page with an error message. Try again, or sign in with email and password instead.

!!! info "When the provider says nothing about the address"
    Some providers never say whether they have confirmed an email address. Kamerplanter treats that silence as "unconfirmed" and skips the automatic link. Sign in with email and password, then link the provider in your account settings. You end up in the same place, by a different route.

!!! note "Alternative sign-in options not showing?"
    If the list of external providers fails to load, the sign-in page shows a message. You can still sign in with email and password in this case.

### Temporary Account Lock

After several failed sign-in attempts in a row, the system temporarily locks your account to protect it from automated attacks. The lockout starts at a few minutes and increases with further failed attempts — the sign-in form shows how much longer the lock lasts. Wait until the lock expires or reset your password (see below).

---

## Forgot and Reset Your Password

1. On the sign-in page, click **Forgot password?**
2. Enter your email address and click **Send Reset Link**
3. You see the confirmation **If an account with this email exists, a reset link has been sent**

!!! note "Why this message always appears"
    This message is shown regardless of whether an account with the entered address exists. It prevents outsiders from using the reset feature to discover which email addresses are registered with Kamerplanter.

4. Open the reset link from the email (valid for **1 hour**)
5. Choose a new password (at least 10 characters) and confirm it
6. Click **Save Password** — you are redirected to the sign-in page

---

## Managing Profile, Language and Timezone

Open your account settings via your profile picture or initials in the top right of the navigation bar.

In the **Profile** tab you can change:

| Setting | Description |
|---------|-------------|
| **Display Name** | Shown throughout the app |
| **Email** | Display only — the sign-in email cannot be changed here |
| **Language** | German or English — switches the interface language immediately |
| **Timezone** | Used for all date and time displays, e.g. `Europe/Berlin` |

Click **Save** after making changes.

---

## Changing Your Password and Managing Sign-In Providers

In the **Security** tab of your account settings you manage how you sign in.

### Changing or Setting Your Password

- If you already have a local password, enter your current password and choose a new one
- If you have only ever signed in via an external provider (e.g. Google), you can **set** a local password here as well — without a current password, since none exists yet. Afterwards you can sign in either with email/password or via the provider.

!!! warning "Changing your password ends all sessions"
    As soon as you change your password, all active sessions are terminated — including on other devices. You will need to sign in again there.

### Linked Sign-In Providers

The list shows all sign-in methods linked to your account (local password, Google, GitHub, …). You can unlink a provider as long as at least one other sign-in method remains. Your last remaining sign-in method cannot be removed, so you can never be locked out of your account.

---

## Viewing and Ending Active Sessions

The **Sessions** tab shows all devices and browsers you are currently signed in on:

| Column | Meaning |
|--------|---------|
| **Device** | Browser/device information; your current session is marked |
| **Session Type** | **Persistent** (created with "Remember me", up to 30 days) or **Session** (without it, up to 24 hours) |
| **IP** | IP address the session was created from |
| **Expires** | Expiry date of the session |

To end a session you don't recognize or no longer need, click the trash icon on that row. You cannot end your current session here — for that, use **Log out** in the account menu.

!!! tip "Found a suspicious session?"
    End it immediately, then change your password — that automatically ends all remaining sessions (see above).

---

## Experience Level and Other Settings

In the **Experience** tab of your account settings you can also:

- adjust your experience level (Beginner, Intermediate, Expert) — see [Getting Started — Onboarding](onboarding.md) for details on the three levels
- set your **watering can size**, which is used as a default in dosing calculators
- restart the **setup wizard**, for example to add another scenario

Which functional areas you show or hide independently of your experience level is controlled in the **Modules & Features** tab — see [Modules & Features](module-visibility.md).

In the **API Keys** tab (access tokens for programmatic access, e.g. your own scripts), you can create and revoke personal API keys. See the [API documentation](../api/authentication.md) for details.

---

## Deleting Your Account

In the **Account** tab of your account settings, the red-highlighted area contains the **Delete Account** button. It immediately deactivates your account and removes your sign-in credentials — you can no longer sign in afterwards.

!!! danger "Use the Privacy area for a full GDPR (General Data Protection Regulation) erasure"
    This quick action deactivates your account, but does not replace the full erasure process under GDPR Art. 17 with legally compliant anonymization of your harvest and treatment data. If you want your data fully and traceably erased, use the process described in [Privacy & GDPR](privacy.md#deleting-your-account-gdpr-art-17) instead.

---

## Frequently Asked Questions

??? question "I didn't receive a confirmation email. What can I do?"
    Check your spam folder first. The confirmation link is valid for 24 hours; after that, you need to register again to receive a new email.

??? question "Can I change my email address?"
    In account settings, the email address is display-only and cannot be edited there. Changing your email is part of the privacy features — see [Privacy & GDPR](privacy.md).

??? question "What happens if I unlink a sign-in provider like Google?"
    You will no longer be able to sign in through that provider. As long as at least one other sign-in method (password or another provider) remains, sign-in continues to work through that method.

??? question "Why were all my sessions ended when I only changed my password?"
    This is a security measure: after a password change, all sessions are ended as a precaution so a potentially compromised device no longer has access. You will need to sign in again everywhere.

---

## See Also

- [Getting Started — Onboarding](onboarding.md)
- [Tenants & Gardens](tenants.md)
- [Roles, Tenants & Visibility](../reference/roles-and-permissions.md)
- [Modules & Features](module-visibility.md)
- [Privacy & GDPR](privacy.md)
- [API Documentation: Authentication](../api/authentication.md)
