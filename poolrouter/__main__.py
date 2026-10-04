import uvicorn


def main() -> None:
    uvicorn.run("poolrouter.api.app:app", host="127.0.0.1", port=4000, reload=False)


if __name__ == "__main__":
    main()
