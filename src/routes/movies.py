from http.client import HTTPResponse
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, MovieModel
from schemas import MovieListResponseSchema, MovieDetailResponseSchema

router = APIRouter()


@router.get("/movies/", response_model=MovieListResponseSchema)
async def read_movies(
        db: Annotated[AsyncSession, Depends(get_db)],
        page: int = 1,
        per_page: int = 10
):
    if not page >= 1:
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "loc": ["query", "page"],
                    "msg": "Input should be greater than or equal to 1",
                    "type": "value_error.number.not_ge"
                }
            ]
        )
    if not per_page >= 1:
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "loc": ["query", "per_page"],
                    "msg": "Input should be greater than or equal to 1",
                    "type": "value_error.number.not_ge"
                }
            ]
        )

    total_items = await db.scalar(
        select(func.count()).select_from(MovieModel)
    )

    if total_items <= 0:
        raise HTTPException(
            status_code=404,
            detail="No movies found."
        )

    total_pages = (total_items + per_page - 1) // per_page

    if page > total_pages:
        raise HTTPException(
            status_code=404,
            detail="No movies found."
        )

    result = await db.scalars(
        select(MovieModel).offset((int(page) - 1) * int(per_page)).limit(per_page)
    )

    movies = result.all()

    return MovieListResponseSchema(
        movies=movies,
        prev_page=(page - 1) if page != 1 else None,
        next_page=(page + 1) if page != total_pages else None,
        total_pages=total_pages,
        total_items=total_items
    )


@router.get("/movies/{movie_id}/", response_model=MovieDetailResponseSchema)
async def read_single_movies(
        db: Annotated[AsyncSession, Depends(get_db)],
        movie_id: int
):
    result = await db.get(MovieModel, movie_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    return result
