from collections import defaultdict
from datetime import datetime, timezone

published_posts = set()

last_check_time = defaultdict(lambda: datetime.now(timezone.utc))