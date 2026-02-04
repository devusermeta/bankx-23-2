"""
Date normalization utility for BankX Financial Operations.
Handles natural language date parsing with Asia/Bangkok timezone (+07:00).

Key Features:
- Normalize natural language dates ("last Friday", "this week", "yesterday")
- Always use Asia/Bangkok timezone (+07:00)
- ISO 8601 format output
- Week convention: Monday-Sunday
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Tuple, Optional
import re


BANGKOK_TZ = ZoneInfo("Asia/Bangkok")


class DateNormalizer:
    """
    Normalizes natural language dates to ISO 8601 format with Asia/Bangkok timezone.

    Examples:
        "last Friday" -> ("2025-10-24", "2025-10-24")
        "this week" -> ("2025-10-20", "2025-10-26")
        "yesterday" -> ("2025-10-26", "2025-10-26")
    """

    def __init__(self, reference_date: Optional[datetime] = None):
        """
        Initialize with optional reference date (for testing).

        Args:
            reference_date: Reference date for relative calculations. Defaults to now in Bangkok.
        """
        if reference_date:
            self.now = reference_date.astimezone(BANGKOK_TZ)
        else:
            self.now = datetime.now(BANGKOK_TZ)

    def normalize(self, natural_language_date: str) -> Tuple[str, str]:
        """
        Normalize natural language date to (from_date, to_date) tuple.

        Args:
            natural_language_date: Natural language date expression

        Returns:
            Tuple of (from_date, to_date) in YYYY-MM-DD format

        Examples:
            >>> normalizer = DateNormalizer()
            >>> normalizer.normalize("last Friday")
            ("2025-10-24", "2025-10-24")
        """
        nl_date = natural_language_date.lower().strip()

        # Today
        if nl_date in ["today"]:
            return self._format_date(self.now), self._format_date(self.now)

        # Yesterday
        if nl_date in ["yesterday"]:
            yesterday = self.now - timedelta(days=1)
            return self._format_date(yesterday), self._format_date(yesterday)

        # Tomorrow
        if nl_date in ["tomorrow"]:
            tomorrow = self.now + timedelta(days=1)
            return self._format_date(tomorrow), self._format_date(tomorrow)

        # Last N days (e.g., "last 7 days", "past 3 days")
        match = re.search(r'(?:last|past)\s+(\d+)\s+days?', nl_date)
        if match:
            days = int(match.group(1))
            from_date = self.now - timedelta(days=days)
            return self._format_date(from_date), self._format_date(self.now)

        # This week (Monday-Sunday)
        if nl_date in ["this week"]:
            return self._get_week_range(self.now)

        # Last week (previous Monday-Sunday)
        if nl_date in ["last week"]:
            last_week = self.now - timedelta(weeks=1)
            return self._get_week_range(last_week)

        # This month
        if nl_date in ["this month"]:
            first_day = self.now.replace(day=1)
            # Last day of current month
            if self.now.month == 12:
                next_month = self.now.replace(year=self.now.year + 1, month=1, day=1)
            else:
                next_month = self.now.replace(month=self.now.month + 1, day=1)
            last_day = next_month - timedelta(days=1)
            return self._format_date(first_day), self._format_date(last_day)

        # Last month
        if nl_date in ["last month"]:
            first_of_this_month = self.now.replace(day=1)
            last_of_last_month = first_of_this_month - timedelta(days=1)
            first_of_last_month = last_of_last_month.replace(day=1)
            return self._format_date(first_of_last_month), self._format_date(last_of_last_month)

        # Specific weekday (e.g., "last Friday", "last Monday")
        weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }

        for day_name, day_num in weekdays.items():
            if f"last {day_name}" in nl_date:
                target_date = self._get_last_weekday(day_num)
                return self._format_date(target_date), self._format_date(target_date)

            if f"next {day_name}" in nl_date:
                target_date = self._get_next_weekday(day_num)
                return self._format_date(target_date), self._format_date(target_date)

        # Specific month (e.g., "October", "October 2025")
        month_names = [
            'january', 'february', 'march', 'april', 'may', 'june',
            'july', 'august', 'september', 'october', 'november', 'december'
        ]

        for idx, month_name in enumerate(month_names, 1):
            if month_name in nl_date:
                # Extract year if present
                year_match = re.search(r'(\d{4})', nl_date)
                year = int(year_match.group(1)) if year_match else self.now.year

                first_day = datetime(year, idx, 1, tzinfo=BANGKOK_TZ)
                # Last day of month
                if idx == 12:
                    next_month = datetime(year + 1, 1, 1, tzinfo=BANGKOK_TZ)
                else:
                    next_month = datetime(year, idx + 1, 1, tzinfo=BANGKOK_TZ)
                last_day = next_month - timedelta(days=1)

                return self._format_date(first_day), self._format_date(last_day)

        # Specific date range (e.g., "October 20 to October 22", "Oct 20-22")
        # Pattern: "Month Day to Month Day" or "Month Day - Day"
        range_match = re.search(
            r'(\w+)\s+(\d{1,2})(?:\s+to\s+|\s*-\s*)(?:(\w+)\s+)?(\d{1,2})',
            nl_date
        )
        if range_match:
            month1_str = range_match.group(1)
            day1 = int(range_match.group(2))
            month2_str = range_match.group(3) or month1_str  # Same month if not specified
            day2 = int(range_match.group(4))

            # Find month numbers
            month1 = self._month_name_to_number(month1_str)
            month2 = self._month_name_to_number(month2_str)

            if month1 and month2:
                year = self.now.year
                from_date = datetime(year, month1, day1, tzinfo=BANGKOK_TZ)
                to_date = datetime(year, month2, day2, tzinfo=BANGKOK_TZ)
                return self._format_date(from_date), self._format_date(to_date)

        # Specific single date (e.g., "October 24", "Oct 24")
        single_date_match = re.search(r'(\w+)\s+(\d{1,2})(?:\s+(\d{4}))?', nl_date)
        if single_date_match:
            month_str = single_date_match.group(1)
            day = int(single_date_match.group(2))
            year = int(single_date_match.group(3)) if single_date_match.group(3) else self.now.year

            month = self._month_name_to_number(month_str)
            if month:
                target_date = datetime(year, month, day, tzinfo=BANGKOK_TZ)
                return self._format_date(target_date), self._format_date(target_date)

        # ISO date format (YYYY-MM-DD)
        iso_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', nl_date)
        if iso_match:
            return iso_match.group(0), iso_match.group(0)

        # If no pattern matches, return today as fallback
        # In production, this should raise an error for unknown patterns
        return self._format_date(self.now), self._format_date(self.now)

    def _get_week_range(self, date: datetime) -> Tuple[str, str]:
        """Get Monday-Sunday range for the week containing the given date."""
        # 0 = Monday, 6 = Sunday
        weekday = date.weekday()
        monday = date - timedelta(days=weekday)
        sunday = monday + timedelta(days=6)
        return self._format_date(monday), self._format_date(sunday)

    def _get_last_weekday(self, target_weekday: int) -> datetime:
        """
        Get the most recent occurrence of a specific weekday.

        Args:
            target_weekday: 0=Monday, 1=Tuesday, ..., 6=Sunday

        Returns:
            datetime of the last occurrence
        """
        current_weekday = self.now.weekday()

        # If target is same as today, go back 7 days
        if current_weekday == target_weekday:
            return self.now - timedelta(days=7)

        # Calculate days to go back
        if current_weekday > target_weekday:
            days_back = current_weekday - target_weekday
        else:
            days_back = 7 - (target_weekday - current_weekday)

        return self.now - timedelta(days=days_back)

    def _get_next_weekday(self, target_weekday: int) -> datetime:
        """Get the next occurrence of a specific weekday."""
        current_weekday = self.now.weekday()

        # If target is same as today, go forward 7 days
        if current_weekday == target_weekday:
            return self.now + timedelta(days=7)

        # Calculate days to go forward
        if target_weekday > current_weekday:
            days_forward = target_weekday - current_weekday
        else:
            days_forward = 7 - (current_weekday - target_weekday)

        return self.now + timedelta(days=days_forward)

    def _month_name_to_number(self, month_str: str) -> Optional[int]:
        """Convert month name (full or abbreviated) to month number."""
        month_map = {
            'jan': 1, 'january': 1,
            'feb': 2, 'february': 2,
            'mar': 3, 'march': 3,
            'apr': 4, 'april': 4,
            'may': 5,
            'jun': 6, 'june': 6,
            'jul': 7, 'july': 7,
            'aug': 8, 'august': 8,
            'sep': 9, 'sept': 9, 'september': 9,
            'oct': 10, 'october': 10,
            'nov': 11, 'november': 11,
            'dec': 12, 'december': 12
        }
        return month_map.get(month_str.lower())

    def _format_date(self, dt: datetime) -> str:
        """Format datetime to YYYY-MM-DD string."""
        return dt.strftime("%Y-%m-%d")

    def get_iso_timestamp(self, dt: Optional[datetime] = None) -> str:
        """
        Get ISO 8601 timestamp with Bangkok timezone.

        Args:
            dt: datetime to format, defaults to now

        Returns:
            ISO 8601 string with +07:00 suffix
        """
        if dt is None:
            dt = self.now
        else:
            dt = dt.astimezone(BANGKOK_TZ)

        return dt.isoformat()

    def get_rationale(
        self,
        nl_query: str,
        from_date: str,
        to_date: str,
        additional_context: Optional[str] = None
    ) -> str:
        """
        Generate human-readable rationale for date normalization.

        Args:
            nl_query: Original natural language query
            from_date: Normalized from_date
            to_date: Normalized to_date
            additional_context: Optional additional context

        Returns:
            Human-readable rationale string
        """
        current_date = self._format_date(self.now)
        current_day = self.now.strftime("%A")  # Monday, Tuesday, etc.

        rationale = (
            f"Date normalization: '{nl_query}' "
            f"relative to {current_day} {current_date} "
            f"=> {from_date} to {to_date}. "
        )

        if from_date == to_date:
            rationale += "Single-day query. "
        else:
            days = (datetime.fromisoformat(to_date) - datetime.fromisoformat(from_date)).days + 1
            rationale += f"{days}-day period. "

        if additional_context:
            rationale += additional_context

        return rationale


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def normalize_date(natural_language_date: str) -> Tuple[str, str]:
    """
    Convenience function for date normalization.

    Args:
        natural_language_date: Natural language date string

    Returns:
        Tuple of (from_date, to_date) in YYYY-MM-DD format
    """
    normalizer = DateNormalizer()
    return normalizer.normalize(natural_language_date)


def get_bangkok_timestamp() -> str:
    """Get current timestamp in Asia/Bangkok timezone (ISO 8601)."""
    return datetime.now(BANGKOK_TZ).isoformat()


def get_bangkok_date() -> str:
    """Get current date in Asia/Bangkok timezone (YYYY-MM-DD)."""
    return datetime.now(BANGKOK_TZ).strftime("%Y-%m-%d")


# ============================================================================
# EXAMPLES & TESTS
# ============================================================================

if __name__ == "__main__":
    # Test examples from specification
    print("Testing DateNormalizer with examples from specification...\n")

    # Example 1: Somchai views Friday transactions
    # Current: Monday, October 27, 2025
    test_date = datetime(2025, 10, 27, 14, 30, 0, tzinfo=BANGKOK_TZ)
    normalizer = DateNormalizer(reference_date=test_date)

    result = normalizer.normalize("last Friday")
    print(f"'last Friday' on Monday Oct 27 => {result}")
    print(f"Expected: ('2025-10-24', '2025-10-24')")
    print(f"Match: {result == ('2025-10-24', '2025-10-24')}\n")

    # Example 2: Nattaporn views this week
    # Current: Saturday, October 26, 2025
    test_date = datetime(2025, 10, 26, 15, 30, 0, tzinfo=BANGKOK_TZ)
    normalizer = DateNormalizer(reference_date=test_date)

    result = normalizer.normalize("this week")
    print(f"'this week' on Saturday Oct 26 => {result}")
    print(f"Expected: ('2025-10-20', '2025-10-26')")
    print(f"Match: {result == ('2025-10-20', '2025-10-26')}\n")

    # Example 3: Pimchanok views specific range
    # Current: Sunday, October 27, 2025
    test_date = datetime(2025, 10, 27, 16, 0, 0, tzinfo=BANGKOK_TZ)
    normalizer = DateNormalizer(reference_date=test_date)

    result = normalizer.normalize("October 20 to October 22")
    print(f"'October 20 to October 22' => {result}")
    print(f"Expected: ('2025-10-20', '2025-10-22')")
    print(f"Match: {result == ('2025-10-20', '2025-10-22')}\n")

    # Test rationale generation
    rationale = normalizer.get_rationale(
        "last Friday",
        "2025-10-24",
        "2025-10-24",
        "Single account customer, no disambiguation needed."
    )
    print(f"Rationale: {rationale}")
