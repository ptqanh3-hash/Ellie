from pathlib import Path

from PIL import Image


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    source = root / "Logo" / "EliieAppN.png"
    output = root / "build" / "ellie.ico"
    output.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(source).convert("RGBA")
    image.save(
        output,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
