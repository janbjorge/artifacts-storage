from __future__ import annotations

from utils import loader


def main() -> None:
    for file, data in loader():
        if data.github_ref_name != "main":
            file.unlink()
            print(file)


if __name__ == "__main__":
    main()
