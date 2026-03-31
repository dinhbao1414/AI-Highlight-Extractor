import io
import sys


def configure_stdio() -> None:
    """Force UTF-8 stdio on Windows consoles when possible."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue

        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
            continue
        except Exception:
            pass

        buffer = getattr(stream, "buffer", None)
        if buffer is None:
            continue

        try:
            wrapped = io.TextIOWrapper(buffer, encoding="utf-8", errors="replace")
            setattr(sys, stream_name, wrapped)
        except Exception:
            pass


def safe_print(*args, **kwargs) -> None:
    """Print without crashing on terminals that cannot encode Unicode."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        file = kwargs.get("file", sys.stdout)
        text = sep.join(str(arg) for arg in args)
        file.write(text.encode("utf-8", errors="replace").decode("utf-8", errors="replace") + end)
