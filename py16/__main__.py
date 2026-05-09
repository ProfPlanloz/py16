"""
Entry point for 'python -m py16' and the 'py16' command.

Behavior:
  py16                  -> starts without cart, opens BIOS or boot cart
  py16 cart.p16         -> starts the given cart directly
  py16 cart.pdf         -> dito
  py16 --cleanup-cache  -> cleans the PDF cover cache
  py16 --cache-stats    -> shows cache stats
"""

import sys
import os

def _format_bytes(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

def _cmd_cache_stats():
    from py16 import cart_covers
    stats = cart_covers.cache_stats()
    print(f"Cache directory: {cart_covers._cache_dir()}")
    print(f"  Files:      {stats['count']}")
    print(f"  Total size: {_format_bytes(stats['total_bytes'])}")
    if stats['oldest']:
        import datetime
        oldest = datetime.datetime.fromtimestamp(stats['oldest']).isoformat(' ', 'seconds')
        newest = datetime.datetime.fromtimestamp(stats['newest']).isoformat(' ', 'seconds')
        print(f"  Oldest:     {oldest}")
        print(f"  Newest:     {newest}")
    return 0

def _cmd_cleanup_cache(args):
    """Parse remaining args after --cleanup-cache."""
    from py16 import cart_covers

    max_age = None
    max_size = None
    no_orphans = False
    dry_run = False

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--age" and i + 1 < len(args):
            max_age = int(args[i + 1]); i += 2
        elif a == "--size" and i + 1 < len(args):
            max_size = int(args[i + 1]); i += 2
        elif a == "--no-orphans":
            no_orphans = True; i += 1
        elif a == "--dry-run":
            dry_run = True; i += 1
        else:
            print(f"Unknown option: {a}")
            print("Usage: py16 --cleanup-cache [--age N] [--size N] [--no-orphans] [--dry-run]")
            return 1

    print(f"Running cleanup (dry_run={dry_run})...")
    if not no_orphans:
        print("  - removing orphans (cache entries whose source PDF is gone)")
    if max_age is not None:
        print(f"  - removing entries older than {max_age} days")
    if max_size is not None:
        print(f"  - keeping total cache below {max_size} MB")

    result = cart_covers.cleanup_cache(
        max_age_days=max_age,
        max_size_mb=max_size,
        remove_orphans=not no_orphans,
        dry_run=dry_run,
    )

    action = "Would remove" if dry_run else "Removed"
    print(f"\n{action}: {result['removed']} files ({_format_bytes(result['freed_bytes'])} freed)")
    print(f"Kept:    {result['kept']} files")
    if dry_run and result['removed_files']:
        print("\nFiles that would be removed:")
        for f in result['removed_files'][:20]:
            print(f"  {f}")
        if len(result['removed_files']) > 20:
            print(f"  ... and {len(result['removed_files']) - 20} more")
    return 0

def main():
    args = sys.argv[1:]

    # Maintenance commands - don't open a window
    if args and args[0] == "--cleanup-cache":
        sys.exit(_cmd_cleanup_cache(args[1:]))
    if args and args[0] == "--cache-stats":
        sys.exit(_cmd_cache_stats())
    if args and args[0] in ("--help", "-h"):
        print(__doc__)
        sys.exit(0)

    import py16

    if not args:
        # No cart - BIOS / Auto-boot
        py16.run()
        return

    cart_path = args[0]
    if not os.path.exists(cart_path):
        print(f"Cart not found: {cart_path}")
        sys.exit(1)

    py16.load_cart(cart_path)
    py16.run_cart(cart_path)
    py16.run()

if __name__ == "__main__":
    main()
