import warnings; warnings.filterwarnings("ignore")
from app.main import app
from fastapi.routing import APIRoute
def deps(d, acc):
    for x in d.dependencies:
        n = getattr(x.call, "__qualname__", str(x.call))
        acc.add(n); deps(x, acc)
    return acc
rows=[]
def walk(routes, prefix=""):
    for r in routes:
        if hasattr(r, "original_router"):
            ctx = getattr(r, "include_context", None)
            p = getattr(ctx, "prefix", "") or ""
            yield from walk(r.original_router.routes, prefix + p)
        else:
            yield prefix, r
for prefix, r in walk(app.routes):
    if isinstance(r, APIRoute):
        a = deps(r.dependant, set())
        auth = "platform_admin" if any("require_platform_admin" in n for n in a) else \
               "role" if any("require_roles" in n for n in a) else \
               "principal" if any("get_principal" in n for n in a) else "PUBLIC"
        rows.append((prefix + r.path, ",".join(sorted(r.methods)), auth, r.endpoint.__module__.split(".")[-1]))
for row in sorted(rows): print("\t".join(row))
