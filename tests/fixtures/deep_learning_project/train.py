import torch


def main() -> None:
    print(torch.cuda.is_available())


if __name__ == "__main__":
    main()
