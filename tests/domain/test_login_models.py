from pymax.types.domain import Login2Response, LoginResponse
from pymax.types.domain.sync import SyncState
from tests.conftest import profile_payload, user_payload


def test_login_response_accepts_login2_deferred_profile() -> None:
    response = LoginResponse.model_validate(
        {
            "chats": [],
            "messages": {},
            "config": {},
            "time": 1783438624879,
            "updates": 1,
            "login2Flags": {
                "contactEnabled": True,
                "configEnabled": True,
                "profileEnabled": True,
            },
        }
    )

    assert response.profile is None
    assert response.login2_flags is not None
    assert response.login2_flags.enabled is True
    assert response.login2_flags.profile_enabled is True


def test_login2_response_maps_contact_infos() -> None:
    response = Login2Response.model_validate(
        {
            "profile": profile_payload(42),
            "contactInfos": [user_payload(43)],
            "config": {"hash": "cfg-hash"},
        }
    )

    assert response.profile is not None
    assert response.profile.contact.id == 42
    assert response.contacts[0] is not None
    assert response.contacts[0].id == 43
    assert response.config is not None
    assert response.config.hash == "cfg-hash"


def test_login2_response_updates_only_config_sync_state() -> None:
    response = Login2Response.model_validate({"config": {"hash": "new-hash"}})
    current = SyncState(
        chats_sync=1,
        contacts_sync=2,
        drafts_sync=3,
        presence_sync=4,
        config_hash="old-hash",
    )

    updated = response.update_sync_state(current)

    assert updated == SyncState(
        chats_sync=1,
        contacts_sync=2,
        drafts_sync=3,
        presence_sync=4,
        config_hash="new-hash",
    )
