def truncate_str(s: str, length: int):
    return s[:length] + "..." if len(s) > length else s
