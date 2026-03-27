# Profile Management

## Purpose

Use this walkthrough to edit the currently supported customer profile fields and to understand which profile tabs are intentionally unavailable.

## Current State Summary

| Item | Current behavior |
| --- | --- |
| Role required | `customer` |
| Main navigation access | Profile dropdown -> `My Profile` |
| Primary route | `/profile` |
| Working status | Partially implemented by design |

## Exact Click Path

1. Open the profile dropdown in the header.
2. Click `My Profile`.
3. Click `Edit Profile`.
4. Update `Full Name` or `Phone Number`.
5. Click `Save Changes`.

## Step-by-step walkthrough

1. Open `/profile`.
2. Confirm the page title is `My Profile`.
3. In the `Personal Information` tab, verify you can see:
   - initials avatar
   - full name
   - email address
   - member-since date
4. Click `Edit Profile`.
5. Update `Full Name`.
6. Optionally update `Phone Number`.
7. Leave `Email Address` alone because it is intentionally read-only.
8. Click `Save Changes`.
9. Confirm the form returns to view mode on success.

## What the other tabs mean today

The following tabs are present but intentionally show unsupported-state cards:

1. `Addresses`
2. `Payment Methods`
3. `Security`
4. `Preferences`

When you click one of those tabs, the page should say `Feature unavailable` and explain that the current API contract does not support that area yet.

## Success checklist

| Check | Expected result |
| --- | --- |
| Edit mode | `Save Changes` and `Cancel` buttons appear |
| Save flow | The page exits edit mode after a successful mutation |
| Unsupported tabs | Explicit unavailable messages render instead of fake data |
