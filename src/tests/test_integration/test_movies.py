import random
import pytest
from sqlalchemy import select, func

from database import MovieModel


@pytest.mark.asyncio
async def test_get_movies_empty_database(client):
    """
    Test retrieving movies from an empty database.

    Expected:
        - 404 response status code.
        - JSON response with a "No movies found." error.
    """
    response = await client.get("/api/v1/theater/movies/")

    assert response.status_code == 404
    assert response.json() == {"detail": "No movies found."}


@pytest.mark.asyncio
async def test_get_movies_default_parameters(client, seed_database):
    """
    Test retrieving movies with default pagination parameters.

    Expected:
        - 200 response status code.
        - 10 movies returned (default `per_page`).
        - Pagination metadata (`total_pages`, `total_items`, `prev_page`, `next_page`).
    """
    response = await client.get("/api/v1/theater/movies/")
    assert response.status_code == 200

    response_data = response.json()
    assert len(response_data["movies"]) == 10
    assert response_data["total_pages"] > 0
    assert response_data["total_items"] > 0
    assert response_data["prev_page"] is None
    if response_data["total_pages"] > 1:
        assert response_data["next_page"] is not None


@pytest.mark.asyncio
async def test_get_movies_with_custom_parameters(client, seed_database):
    """
    Test retrieving movies with custom pagination parameters.

    Expected:
        - 200 response status code.
        - Requested number of movies (`per_page`).
        - Correct `prev_page` and `next_page` links based on pagination.
    """
    page = 2
    per_page = 5

    response = await client.get(f"/api/v1/theater/movies/?page={page}&per_page={per_page}")
    assert response.status_code == 200

    response_data = response.json()
    assert len(response_data["movies"]) == per_page
    assert response_data["total_pages"] > 0
    assert response_data["total_items"] > 0
    if page > 1:
        assert response_data["prev_page"] is not None
    if page < response_data["total_pages"]:
        assert response_data["next_page"] is not None
    else:
        assert response_data["next_page"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("page, per_page, expected_detail", [
    (0, 10, "ensure this value is greater than or equal to 1"),
    (1, 0, "ensure this value is greater than or equal to 1"),
    (0, 0, "ensure this value is greater than or equal to 1"),
])
async def test_invalid_page_and_per_page(client, page, per_page, expected_detail):
    """
    Test invalid pagination parameters.

    Expected:
        - 422 response status code.
        - JSON validation error with the expected message.
    """
    response = await client.get(f"/api/v1/theater/movies/?page={page}&per_page={per_page}")
    assert response.status_code == 422

    response_data = response.json()
    assert any(expected_detail in error["msg"] for error in response_data["detail"])


@pytest.mark.asyncio
async def test_per_page_maximum_allowed_value(client, seed_database):
    """
    Test retrieving movies with the maximum allowed `per_page` value.

    Expected:
        - 200 response status code.
        - A maximum of 20 movies in the response.
    """
    response = await client.get("/api/v1/theater/movies/?page=1&per_page=20")
    assert response.status_code == 200

    response_data = response.json()
    assert "movies" in response_data
    assert len(response_data["movies"]) <= 20


@pytest.mark.asyncio
async def test_page_exceeds_maximum(client, db_session, seed_database):
    """
    Test retrieving a page number that exceeds the total available pages.

    Expected:
        - 404 response status code.
        - JSON response with a "No movies found." error.
    """
    per_page = 10
    total_movies = await db_session.scalar(select(func.count()).select_from(MovieModel))
    max_page = (total_movies + per_page - 1) // per_page

    response = await client.get(f"/api/v1/theater/movies/?page={max_page + 1}&per_page={per_page}")
    assert response.status_code == 404
    assert response.json()["detail"] == "No movies found."


@pytest.mark.asyncio
async def test_get_movie_by_id_not_found(client):
    """
    Test retrieving a movie by an ID that does not exist.

    Expected:
        - 404 response status code.
        - JSON response with a "Movie with the given ID was not found." error.
    """
    movie_id = 1
    response = await client.get(f"/api/v1/theater/movies/{movie_id}/")
    assert response.status_code == 404
    assert response.json() == {"detail": "Movie with the given ID was not found."}


@pytest.mark.asyncio
async def test_get_movie_by_id_valid(client, db_session, seed_database):
    """
    Test retrieving a valid movie by ID.

    Expected:
        - 200 response status code.
        - JSON response containing the correct movie details.
    """
    min_id = (await db_session.execute(select(MovieModel.id).order_by(MovieModel.id.asc()))).scalars().first()
    max_id = (await db_session.execute(select(MovieModel.id).order_by(MovieModel.id.desc()))).scalars().first()
    random_id = random.randint(min_id, max_id)

    expected_movie = await db_session.get(MovieModel, random_id)
    assert expected_movie is not None

    response = await client.get(f"/api/v1/theater/movies/{random_id}/")
    assert response.status_code == 200

    response_data = response.json()
    assert response_data["id"] == expected_movie.id
    assert response_data["name"] == expected_movie.name
    assert response_data["date"] == str(expected_movie.date)
    assert response_data["score"] == expected_movie.score
    assert response_data["genre"] == expected_movie.genre
    assert response_data["overview"] == expected_movie.overview
    assert response_data["crew"] == expected_movie.crew
    assert response_data["orig_title"] == expected_movie.orig_title
    assert response_data["status"] == expected_movie.status
    assert response_data["orig_lang"] == expected_movie.orig_lang
    assert response_data["budget"] == float(expected_movie.budget)
    assert response_data["revenue"] == expected_movie.revenue
    assert response_data["country"] == expected_movie.country
