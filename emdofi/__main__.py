from argparse import ArgumentParser
from emdofi import match

DEFAULT = "*?"

def main() -> None:
    parser = ArgumentParser(prog="EMDOFI - Uncover a censored domain")
    parser.add_argument("domain", type=str, help="The censored domain or email")
    parser.add_argument("-c", "--censored", metavar="CC", type=str, default=DEFAULT, help=f'The censored characters (default: "{DEFAULT}")')
    args = parser.parse_args()

    found = match(args.domain, censored_chars=args.censored)
    if found:
        print(f"[+] Domains matching for {args.domain}:")
        for dom in found:
            print(f"[-] {dom}")
        print("[=] EMDOFI, Made by aet\n    https://twitter.com/meakaaet")
    else:
        print(f"[x] No domains matching {args.domain} were found")

if __name__ == "__main__":
    main()