from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, TextIO
from json import loads
from re import match as rematch
from asyncio import run, gather

_current_path = Path(__file__)
_default_domains_path = _current_path.parent / "domains/all_email_provider_domains.txt"
_re_pattern = r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$"

def scheme_builder(
    domain: str,
    censored_chars: str = []
) -> dict:
    """
        ```
        >>> scheme_builder(
        ...     domain = "g****.**m",
        ...     censored_chars = ["*"]
        ... )
        {0: "g", 5: ".", 8: "m"}
        ```
    """
    return {x: char for x, char in enumerate(domain) if char not in censored_chars}

@dataclass
class CensoredDomain:
    domain: str
    censored_chars: list[str]

    def __post_init__(self) -> None:
        self.scheme = scheme_builder(self.domain, self.censored_chars)
        """
            >>> C = CensoredDomain("g****.**m", ["*"])
            >>> C.scheme
            {0: "g", 5: ".", 8: "m"}
        """

    def __len__(self) -> int:
        return len(self.domain)
    
    def __repr__(self) -> str:
        return self.domain

@dataclass
class SingleDomain:
    """
        ```
        >>> domain = SingleDomain("gmail.com")
        >>> 
        >>> # Possible arguments:
        >>> domain: str
        >>> valid: bool = None
        >>>
        >>> # Argument `valid` is used to check the validity of
        >>> # the domain. If you want to force it, set it on `True`
        ```
    """
    domain: str
    valid: bool = None

    def __post_init__(self) -> None:
        if self.valid is None:
            if 0 < self.domain.count(".") < 4:
                self.valid = bool(rematch(
                    pattern = _re_pattern,
                    string = self.domain
                ))
            else:
                self.valid = False

        self.lenght = len(self.domain)
        self.scheme = scheme_builder(self.domain)

    def __repr__(self) -> str:
        return self.domain

    def __len__(self) -> int:
        return self.lenght

    def __hash__(self) -> int:
        return hash(self.domain)

    async def match(
        self,
        censored_domain: CensoredDomain
    ) -> bool:
        """
            ```
            >>> C = CensoredDomain("g****.**m", ["*"])
            >>> S = SingleDomain("gmail.com")
            >>> S.match(C)
            True
            ```
        """
        assert isinstance(censored_domain, CensoredDomain)

        if len(censored_domain) == self.lenght:
            for key, value in censored_domain.scheme.items():
                if self.scheme[key] != value:
                    break
            else:
                return True

        return False
            
@dataclass
class DomainFinder:
    """
        This object allows to find a censored domain by using it as following:
        ```
        >>> from emdofi import SingleDomain
        >>> refdomains = [
        ...     "gmail.com",                # Domains can be `str`
        ...     "yahoo.com",
        ...     SingleDomain("icloud.com")  # But also `SingleDomain`, containing the `str`
        ... ]
        >>> cens_chars = "*"        # Censored chars can be single `str`
        >>> cens_chars = "*", "?"   # But also `Iterable` of `str`
        >>>
        >>> domain_finder = DomainFinder(       # DomainFinder can be initialized with
        ...     domains = refdomains,           # the default values written upper,
        ...     censoring_chars = cens_chars
        ... )
        >>> # It can also be loaded from a string or a file,
        >>> # Please check the doc of `DomainFinder.loads`
        >>> # And `DomainFinder.load` for further informations.
        >>>
        >>> # `keep_only_valid_domains` arg on `True` will keep only valid domains
        >>> # (the ones matching `_re_pattern` regex) in the `domains` domains.
    """
    domains: list[SingleDomain] = None
    censoring_chars: list[str] = None
    keep_only_valid_domains: bool = True

    def __post_init__(self) -> None:
        if self.domains is None:
            raise ValueError('"domains" argument in "DomainFinder" must be a list of str')
        else:
            self.domains = [ SingleDomain(d) if isinstance(d, str)
                             else d for d in self.domains ]
            if self.keep_only_valid_domains:
                self.domains = [ domain for domain in self.domains
                                 if domain.valid is True ]
            
        self.change_censoring_chars(
            censoring_chars=self.censoring_chars or "*"
        )
        self._x = 0

    def __iter__(self) -> Iterator[SingleDomain]:
        for domain in self.domains:
            yield domain

    def __len__(self) -> int:
        return len(self.domains)

    def change_censoring_chars(
        self,
        *censoring_chars: Iterable[str] | str,
    ) -> None:
        """
            ```
            >>> # Changes the censoring chars to the ones
            >>> # of the `censoring_chars` argument.
            >>> domain_finder = DomainFinder.load_default()
            >>> domain_finder = change_censoring_chars(
            ...     censoring_chars = "%"
            ... )
            >>> 
            >>> # Warning !
            >>> # Strings longer than 1 will be decomposed:
            >>> "?*", "!"
            ["?", "*", "!"]
            >>> "fffç&", "*", "$$&"
            ["f", "ç", "&", "*", "$"]
        """
        censoring_chars = censoring_chars or "*"
        result = []

        if isinstance(censoring_chars, str):
            censoring_chars = [censoring_chars]

        for chars in censoring_chars:
            result += list(chars)

        self.censoring_chars = list(set(result))

    def match(
        self,
        query: str | CensoredDomain,
        full: bool = False
    ) -> list[str] | dict[str, bool]:
        """
            ```
            >>> domain_finder = DomainFinder.load_default()
            >>> domain_finder.match("g****.**m")
            ["gmail.com", "gmial.com"]
            >>> domain_finder.match("g****.**m", full=True)
            {"gmail.com": True, "...": False, "...": False, "gmial.com": True, ...}
            ```
        """
        if isinstance(query, str):
            query = CensoredDomain(
                domain = query.split("@")[-1],
                censored_chars = self.censoring_chars
            )
        elif isinstance(query, CensoredDomain):
            pass
        else:
            raise TypeError('"query" must be a "str" or "CensoredDomain" object')
        
        async def match_all() -> list[bool]:
            return await gather(*[ domain.match(censored_domain=query)
                                   for domain in self ])
            
        results = dict(zip(self.domains, run(match_all())))
        if full:
            return results
        else:
            return [key for key, value in results.items() if value is True]

    @classmethod
    def loads(
        cls,
        strcontent: str,
        *,
        censoring_chars: Iterable[str] | str = "*"
    ) -> "DomainFinder":
        """
            ```
            >>> # Works for strings containing a domain at each lines (separated by \\n)
            >>> text = '''gmail.com
            ... yahoo.com
            ... icloud.com
            ... '''
            >>> domain_finder = DomainFinder.loads(text)
            >>>
            >>> # But also for json lists
            >>> mylist = '["gmail.com","yahoo.com","icloud.com"]'
            >>> domain_finder = DomainFinder.loads(mylist)
        """
        if strcontent.startswith("["):
            datas = loads(strcontent)
        else:
            datas = strcontent.split("\n")
        datas = [SingleDomain(data) for data in datas]
        return cls(
            domains = datas,
            censoring_chars = censoring_chars
        )

    @classmethod
    def load(
        cls,
        readobj: TextIO,
        *,
        censoring_chars: Iterable[str] | str = "*"
    ) -> "DomainFinder":
        """
            ```
            >>> with open("file/path.txt", "r") as read:
            >>>     domain_finder = DomainFinder.load(read)
            ```
        """
        return cls.loads(
            readobj.read(),
            censoring_chars=censoring_chars
        )

    @classmethod
    def load_default(
        cls,
        *,
        censoring_chars: Iterable[str] | str = "*"
    ) -> "DomainFinder":
        """
            Will directly load the default domains database
        """
        with open(_default_domains_path, "r", encoding="utf-8") as _r:
            return cls.load(
                readobj=_r,
                censoring_chars=censoring_chars
            )

def match(
    query: str,
    censored_chars: Iterable[str] = "*"
) -> list[str]:
    """
        - query: str: The censored email or domain to uncover
        - censored_chars: list[str]: The chars that are censoring the domain
    """
    df = DomainFinder.load_default(censoring_chars=censored_chars)
    return df.match(query)