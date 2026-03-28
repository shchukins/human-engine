import requests
from fastapi import HTTPException


def list_activities(access_token: str, per_page: int = 30, page: int = 1):
    response = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        params={
            "per_page": per_page,
            "page": page,
        },
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"strava list activities error {response.status_code}: {response.text[:300]}",
        )

    return response.json()


def fetch_activity(access_token: str, activity_id: int):
    response = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"strava activity api error {response.status_code}: {response.text[:300]}",
        )

    return response.json()


def fetch_activity_streams(access_token: str, activity_id: int):
    response = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity_id}/streams",
        params={
            "keys": "time,distance,latlng,altitude,velocity_smooth,heartrate,cadence,watts,temp,grade_smooth",
            "key_by_type": "true",
        },
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"strava streams api error {response.status_code}: {response.text[:300]}",
        )

    return response.json()
