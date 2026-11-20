"""SQL for the `user_identities` table."""

from core import db


def find(provider, external_id):
    return db.query_one(
        "SELECT * FROM user_identities WHERE provider = ? AND external_id = ?",
        (provider, external_id),
    )


def create(user_id, provider, external_id, raw_profile_json="{}"):
    return db.execute(
        """
        INSERT INTO user_identities (user_id, provider, external_id, raw_profile_json)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, provider, external_id, raw_profile_json),
    )


def update_raw_profile(identity_id, raw_profile_json):
    db.execute(
        "UPDATE user_identities SET raw_profile_json = ? WHERE id = ?",
        (raw_profile_json, identity_id),
    )


def list_for_user(user_id):
    return db.query_all(
        "SELECT * FROM user_identities WHERE user_id = ?", (user_id,)
    )
