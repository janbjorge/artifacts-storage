from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from queries import BenchmarkQueries


def main() -> None:
    with ThreadPoolExecutor() as pool:
        loaded = BenchmarkQueries(pool).load()
    for file, data in loaded:
        if data.github_ref_name != "main":
            file.unlink()
            print(file)


if __name__ == "__main__":
    main()
