from pydantic import PostgresDsn


def build_postgres_dsn(
    host: str,
    port: str,
    user: str,
    password: str,
    dbname: str,
    scheme: str = "postresql+psycopg",
    **kwargs: str | int,
) -> str:
    """Build a postgres dsn from component parts"""
    return str(
        PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=user,
            host=host,
            port=int(port),
            path=dbname,
            password=password,
        )
    )
