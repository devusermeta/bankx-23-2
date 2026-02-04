"""
Cleanup old observability logs
Deletes JSON log files older than N days (default: 1 day)

Usage:
    python observability/cleanup_logs.py              # Delete logs older than 1 day
    python observability/cleanup_logs.py --days 7     # Delete logs older than 7 days
"""

from pathlib import Path
from datetime import datetime, timedelta
import argparse
import sys

def cleanup_old_logs(days_to_keep: int = 1, dry_run: bool = False):
    """
    Delete JSON log files older than N days.
    
    Args:
        days_to_keep: Number of days to keep logs for
        dry_run: If True, only print what would be deleted without actually deleting
    """
    log_dir = Path(__file__).parent
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    print(f"🧹 Cleaning up observability logs older than {days_to_keep} day(s)...")
    print(f"📅 Cutoff date: {cutoff_date.strftime('%Y-%m-%d')}")
    print(f"📁 Log directory: {log_dir.absolute()}")
    print()
    
    deleted_count = 0
    total_size = 0
    
    # Find all JSON log files
    for json_file in log_dir.glob("*.json"):
        try:
            # Extract date from filename (e.g., "agent_decisions_2025-11-11.json")
            # Format: <log_type>_YYYY-MM-DD.json
            parts = json_file.stem.split("_")
            
            # The date should be the last part (YYYY-MM-DD)
            if len(parts) >= 2:
                file_date_str = parts[-1]  # "2025-11-11"
                
                try:
                    file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                    
                    if file_date < cutoff_date:
                        file_size = json_file.stat().st_size
                        total_size += file_size
                        
                        if dry_run:
                            print(f"[DRY RUN] Would delete: {json_file.name} ({file_size:,} bytes)")
                        else:
                            json_file.unlink()
                            print(f"✅ Deleted: {json_file.name} ({file_size:,} bytes)")
                        
                        deleted_count += 1
                    else:
                        print(f"⏭️  Keeping: {json_file.name} (within retention period)")
                        
                except ValueError:
                    # Not a date, skip this file
                    print(f"⚠️  Skipping: {json_file.name} (invalid date format)")
            else:
                print(f"⚠️  Skipping: {json_file.name} (unexpected filename format)")
                
        except Exception as e:
            print(f"❌ Error processing {json_file.name}: {e}")
    
    print()
    print(f"📊 Summary:")
    print(f"   - Files {'would be deleted' if dry_run else 'deleted'}: {deleted_count}")
    print(f"   - Space {'would be freed' if dry_run else 'freed'}: {total_size:,} bytes ({total_size / 1024:.2f} KB)")
    
    if deleted_count == 0:
        print(f"✨ No old logs found. All logs are within the {days_to_keep}-day retention period.")
    
    return deleted_count

def main():
    parser = argparse.ArgumentParser(description="Cleanup old observability JSON logs")
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of days to keep logs for (default: 1)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    
    args = parser.parse_args()
    
    if args.days < 0:
        print("❌ Error: --days must be a positive number")
        sys.exit(1)
    
    try:
        cleanup_old_logs(days_to_keep=args.days, dry_run=args.dry_run)
        print("\n✅ Cleanup completed successfully!")
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
