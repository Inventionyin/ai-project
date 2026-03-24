import time
import logging
from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger("app.db_monitor")
SLOW_QUERY_THRESHOLD = 0.2  # 200ms

def setup_db_monitoring(engine: Engine):
    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.time()

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total_time = time.time() - context._query_start_time
        if total_time > SLOW_QUERY_THRESHOLD:
            logger.warning(
                f"[SLOW SQL] Execution Time: {total_time:.4f}s\n"
                f"Statement: {statement}\n"
                f"Parameters: {parameters}"
            )
