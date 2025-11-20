"""
Data formatting utilities
"""

from typing import Any, Dict, List


def extract_pipeline_info(events: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Extract unique pipeline information from events."""
    pipelines = {}
    
    for event in events:
        if "attributes" not in event:
            continue
            
        attrs = event["attributes"]
        if "attributes" not in attrs:
            continue
            
        event_attrs = attrs["attributes"]
        
        # Extract repository info
        repo_name = "unknown"
        if "git" in event_attrs and "repository" in event_attrs["git"]:
            repo_name = event_attrs["git"]["repository"].get("name", "unknown")
        
        # Extract pipeline info
        if "ci" in event_attrs and "pipeline" in event_attrs["ci"]:
            pipeline = event_attrs["ci"]["pipeline"]
            pipeline_name = pipeline.get("name", "unknown")
            fingerprint = pipeline.get("fingerprint")
            
            if fingerprint:
                # Use fingerprint as key to avoid duplicates
                pipelines[fingerprint] = {
                    "repository": repo_name,
                    "pipeline_name": pipeline_name,
                    "fingerprint": fingerprint,
                }
    
    return sorted(pipelines.values(), key=lambda x: (x["repository"], x["pipeline_name"]))


def format_as_table(pipelines: List[Dict[str, str]]) -> str:
    """Format pipeline data as a table."""
    if not pipelines:
        return "No pipelines found."
    
    # Calculate column widths
    repo_width = max(len("Repository"), max(len(p["repository"]) for p in pipelines))
    name_width = max(len("Pipeline Name"), max(len(p["pipeline_name"]) for p in pipelines))
    finger_width = max(len("Fingerprint"), max(len(p["fingerprint"]) for p in pipelines))
    
    # Create table
    header = f"| {'Repository':<{repo_width}} | {'Pipeline Name':<{name_width}} | {'Fingerprint':<{finger_width}} |"
    separator = f"|{'-' * (repo_width + 2)}|{'-' * (name_width + 2)}|{'-' * (finger_width + 2)}|"
    
    lines = [header, separator]
    for pipeline in pipelines:
        line = f"| {pipeline['repository']:<{repo_width}} | {pipeline['pipeline_name']:<{name_width}} | {pipeline['fingerprint']:<{finger_width}} |"
        lines.append(line)
    
    return "\n".join(lines)


def extract_log_info(log_events: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Extract relevant information from log events."""
    logs = []
    
    for event in log_events:
        # Handle both old format (attributes) and new format (content)
        if "content" in event:
            # New realistic format with content wrapper
            content = event["content"]
            attrs = content.get("attributes", {})
            
            # Extract basic log info from content level
            log_entry = {
                "timestamp": content.get("timestamp", ""),
                "level": content.get("status", attrs.get("level", "unknown")),
                "service": content.get("service", "unknown"),
                "host": content.get("host", "unknown"),
                "message": content.get("message", ""),
            }
            
            # Add tags if available (much more comprehensive now)
            if "tags" in content and isinstance(content["tags"], list):
                # Show only the most relevant tags to avoid clutter
                relevant_tags = []
                for tag in content["tags"]:
                    if any(prefix in tag for prefix in ["env:", "owner:", "project:", "stage:", "region:", "source:"]):
                        relevant_tags.append(tag)
                if relevant_tags:
                    log_entry["tags"] = ", ".join(relevant_tags)
            
        elif "attributes" in event:
            # Old format for backward compatibility
            attrs = event["attributes"]
            
            # Extract basic log info
            log_entry = {
                "timestamp": attrs.get("timestamp", ""),
                "level": attrs.get("status", "unknown"),
                "service": attrs.get("service", "unknown"),
                "host": attrs.get("host", "unknown"),
                "message": attrs.get("message", ""),
            }
            
            # Add tags if available
            if "tags" in attrs and isinstance(attrs["tags"], list):
                log_entry["tags"] = ", ".join(attrs["tags"])
            
            # For old format, attributes are nested under "attributes"
            attrs = attrs.get("attributes", {})
        else:
            continue
        
        # Add additional context from attributes
        if attrs and isinstance(attrs, dict):
            # Add useful extra fields
            if "environment" in attrs:
                log_entry["environment"] = str(attrs["environment"])
            if "duration" in attrs:
                log_entry["duration"] = str(attrs["duration"])
            if "customAttribute" in attrs:
                log_entry["customAttribute"] = str(attrs["customAttribute"])
            
            # Lambda-specific fields
            if "lambda" in attrs and isinstance(attrs["lambda"], dict):
                lambda_info = attrs["lambda"]
                if "name" in lambda_info:
                    log_entry["function"] = str(lambda_info["name"])
                if "arn" in lambda_info:
                    log_entry["lambda_arn"] = str(lambda_info["arn"])
                if "request_id" in lambda_info:
                    log_entry["request_id"] = str(lambda_info["request_id"])
            
            # Task type statistics (specific to caorchestrator)
            if "task_type_stats" in attrs and isinstance(attrs["task_type_stats"], dict):
                task_stats = attrs["task_type_stats"]
                total_tasks = sum(task_stats.values())
                if total_tasks > 0:
                    # Show only non-zero task types
                    active_tasks = [f"{k}:{v}" for k, v in task_stats.items() if v > 0]
                    if active_tasks:
                        log_entry["task_stats"] = ", ".join(active_tasks)
                    log_entry["total_tasks"] = str(total_tasks)
            
            # AWS-specific information
            if "aws" in attrs and isinstance(attrs["aws"], dict):
                aws_info = attrs["aws"]
                if "awslogs" in aws_info:
                    awslogs = aws_info["awslogs"]
                    if "logGroup" in awslogs:
                        log_entry["log_group"] = str(awslogs["logGroup"])
                    if "logStream" in awslogs:
                        # Truncate log stream for readability
                        log_stream = str(awslogs["logStream"])
                        if len(log_stream) > 50:
                            log_stream = log_stream[:47] + "..."
                        log_entry["log_stream"] = log_stream
                
                if "function_version" in aws_info:
                    log_entry["function_version"] = str(aws_info["function_version"])
            
            # Override level if specified in attributes
            if "level" in attrs:
                log_entry["level"] = str(attrs["level"])
            
            # Add other interesting custom attributes (but skip verbose ones)
            skip_attrs = {
                "environment", "duration", "customAttribute", "lambda", "level", 
                "task_type_stats", "aws", "service", "host", "id", "timestamp"
            }
            
            for key, value in attrs.items():
                if key not in skip_attrs:
                    # Convert complex objects to strings, but keep it concise
                    if isinstance(value, dict):
                        if len(value) <= 3:  # Only show small dicts
                            log_entry[f"attr_{key}"] = str(value)
                    elif isinstance(value, list):
                        if len(value) <= 5:  # Only show small lists
                            log_entry[f"attr_{key}"] = str(value)
                    else:
                        log_entry[f"attr_{key}"] = str(value)
        
        logs.append(log_entry)
    
    return logs


def format_logs_as_table(logs: List[Dict[str, str]], max_message_length: int = 80) -> str:
    """Format log data as a table."""
    if not logs:
        return "No logs found."
    
    # Truncate long messages for table display
    display_logs = []
    for log in logs:
        display_log = log.copy()
        message = display_log.get("message", "")
        if len(message) > max_message_length:
            display_log["message"] = message[:max_message_length - 3] + "..."
        display_logs.append(display_log)
    
    # Calculate column widths
    timestamp_width = 20  # Fixed width for timestamp
    level_width = max(len("Level"), max(len(log.get("level", "")) for log in display_logs))
    service_width = max(len("Service"), max(len(log.get("service", "")) for log in display_logs))
    message_width = max(len("Message"), max(len(log.get("message", "")) for log in display_logs))
    
    # Create table
    header = f"| {'Timestamp':<{timestamp_width}} | {'Level':<{level_width}} | {'Service':<{service_width}} | {'Message':<{message_width}} |"
    separator = f"|{'-' * (timestamp_width + 2)}|{'-' * (level_width + 2)}|{'-' * (service_width + 2)}|{'-' * (message_width + 2)}|"
    
    lines = [header, separator]
    for log in display_logs:
        timestamp = log.get("timestamp", "")[:timestamp_width]  # Truncate timestamp if needed
        level = log.get("level", "")
        service = log.get("service", "")
        message = log.get("message", "")
        
        line = f"| {timestamp:<{timestamp_width}} | {level:<{level_width}} | {service:<{service_width}} | {message:<{message_width}} |"
        lines.append(line)
    
    return "\n".join(lines)


def format_logs_as_text(logs: List[Dict[str, str]]) -> str:
    """Format log data as readable text."""
    if not logs:
        return "No logs found."
    
    lines = []
    for log in logs:
        timestamp = log.get("timestamp", "")
        level = log.get("level", "").upper()
        service = log.get("service", "")
        message = log.get("message", "")
        
        line = f"[{timestamp}] {level} {service}: {message}"
        lines.append(line)
        
        # Add additional attributes if present
        attrs_to_show = []
        for key, value in log.items():
            if key not in ["timestamp", "level", "service", "message"] and value:
                attrs_to_show.append(f"{key}: {value}")
        
        if attrs_to_show:
            # Add indented attributes
            for attr in attrs_to_show:
                lines.append(f"  {attr}")
    
    return "\n".join(lines)


def extract_team_info(teams: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Extract relevant information from team data."""
    team_list = []
    
    for team in teams:
        if "attributes" not in team:
            continue
        
        attrs = team["attributes"]
        
        team_info = {
            "id": team.get("id", ""),
            "name": attrs.get("name", "unknown"),
            "handle": attrs.get("handle", ""),
            "description": attrs.get("description", ""),
            "created_at": attrs.get("created_at", ""),
        }
        
        team_list.append(team_info)
    
    return sorted(team_list, key=lambda x: x["name"])


def extract_membership_info(memberships: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Extract relevant information from team membership data."""
    members = []
    
    for membership in memberships:
        if "attributes" not in membership:
            continue
        
        attrs = membership["attributes"]
        
        # Get user info from relationships
        user_info = {}
        if "relationships" in membership and "user" in membership["relationships"]:
            user_data = membership["relationships"]["user"].get("data", {})
            user_info = {
                "user_id": user_data.get("id", ""),
                "user_type": user_data.get("type", ""),
            }
        
        member_info = {
            "user_id": user_info.get("user_id", ""),
            "role": attrs.get("role", "unknown"),
            "position": attrs.get("position", ""),
            "created_at": attrs.get("created_at", ""),
        }
        
        members.append(member_info)
    
    return members


def format_teams_as_table(teams: List[Dict[str, str]]) -> str:
    """Format team data as a table."""
    if not teams:
        return "No teams found."
    
    # Calculate column widths
    name_width = max(len("Team Name"), max(len(t.get("name", "")) for t in teams))
    handle_width = max(len("Handle"), max(len(t.get("handle", "")) for t in teams))
    desc_width = min(50, max(len("Description"), max(len(t.get("description", "")) for t in teams)))
    
    # Create table header
    header = f"| {'Team Name':<{name_width}} | {'Handle':<{handle_width}} | {'Description':<{desc_width}} |"
    separator = f"|{'-' * (name_width + 2)}|{'-' * (handle_width + 2)}|{'-' * (desc_width + 2)}|"
    
    lines = [header, separator]
    for team in teams:
        name = team.get("name", "")
        handle = team.get("handle", "")
        description = team.get("description", "")
        
        # Truncate description if too long
        if len(description) > desc_width:
            description = description[:desc_width - 3] + "..."
        
        line = f"| {name:<{name_width}} | {handle:<{handle_width}} | {description:<{desc_width}} |"
        lines.append(line)
    
    return "\n".join(lines)


def format_team_with_members(team: Dict[str, str], members: List[Dict[str, str]]) -> str:
    """Format team info with its members."""
    lines = []
    
    # Team header
    lines.append(f"Team: {team.get('name', 'Unknown')}")
    lines.append(f"Handle: @{team.get('handle', 'N/A')}")
    if team.get('description'):
        lines.append(f"Description: {team.get('description')}")
    lines.append(f"Created: {team.get('created_at', 'N/A')}")
    lines.append("")
    
    # Members section
    if members:
        lines.append(f"Members ({len(members)}):")
        lines.append("-" * 40)
        
        for member in members:
            role = member.get("role", "unknown")
            position = member.get("position", "")
            user_id = member.get("user_id", "")
            
            member_line = f"• {role}"
            if position:
                member_line += f" - {position}"
            if user_id:
                member_line += f" (ID: {user_id})"
            
            lines.append(member_line)
    else:
        lines.append("No members found.")
    
    return "\n".join(lines)


def extract_metrics_info(metrics_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant information from metrics data."""
    if "series" not in metrics_data or not metrics_data["series"]:
        return {
            "metric": "unknown",
            "points": [],
            "unit": "",
            "status": "no_data"
        }
    
    series = metrics_data["series"][0]  # Take first series
    
    metric_info = {
        "metric": series.get("metric", "unknown"),
        "display_name": series.get("display_name", ""),
        "aggr": series.get("aggr", ""),
        "scope": series.get("scope", ""),
        "points": series.get("pointlist", []),
        "unit": "",
        "status": "ok"
    }
    
    # Extract unit information
    if "unit" in series and series["unit"] and len(series["unit"]) > 0:
        unit_info = series["unit"][0]
        metric_info["unit"] = unit_info.get("short_name", "")
    
    return metric_info


def format_metrics_summary(metrics: Dict[str, Dict[str, Any]]) -> str:
    """Format metrics data as a summary table."""
    if not metrics:
        return "No metrics found."
    
    lines = []
    
    for metric_name, data in metrics.items():
        if "error" in data:
            lines.append(f"❌ {metric_name}: Error - {data['error']}")
            continue
        
        metric_info = extract_metrics_info(data)
        
        if metric_info["status"] == "no_data":
            lines.append(f"⚠️  {metric_name}: No data available")
            continue
        
        points = metric_info["points"]
        if not points:
            lines.append(f"⚠️  {metric_name}: No data points")
            continue
        
        # Calculate basic statistics
        values = [point[1] for point in points if point[1] is not None]
        if not values:
            lines.append(f"⚠️  {metric_name}: No valid values")
            continue
        
        avg_value = sum(values) / len(values)
        min_value = min(values)
        max_value = max(values)
        latest_value = values[-1] if values else 0
        
        unit = metric_info["unit"]
        unit_str = f" {unit}" if unit else ""
        
        lines.append(f"✅ {metric_name}:")
        lines.append(f"   Latest: {latest_value:.2f}{unit_str}")
        lines.append(f"   Avg: {avg_value:.2f}{unit_str}")
        lines.append(f"   Min: {min_value:.2f}{unit_str}")
        lines.append(f"   Max: {max_value:.2f}{unit_str}")
        lines.append(f"   Points: {len(points)}")
        lines.append("")
    
    return "\n".join(lines)


def format_metrics_table(metrics: Dict[str, Dict[str, Any]]) -> str:
    """Format metrics data as a table."""
    if not metrics:
        return "No metrics found."
    
    # Extract data for table
    table_data = []
    
    for metric_name, data in metrics.items():
        if "error" in data:
            table_data.append({
                "metric": metric_name,
                "latest": "Error",
                "avg": "-",
                "min": "-",
                "max": "-",
                "unit": "",
                "points": "0"
            })
            continue
        
        metric_info = extract_metrics_info(data)
        
        if metric_info["status"] == "no_data" or not metric_info["points"]:
            table_data.append({
                "metric": metric_name,
                "latest": "No data",
                "avg": "-",
                "min": "-",
                "max": "-",
                "unit": metric_info["unit"],
                "points": "0"
            })
            continue
        
        points = metric_info["points"]
        values = [point[1] for point in points if point[1] is not None]
        
        if not values:
            table_data.append({
                "metric": metric_name,
                "latest": "No values",
                "avg": "-",
                "min": "-",
                "max": "-",
                "unit": metric_info["unit"],
                "points": str(len(points))
            })
            continue
        
        avg_value = sum(values) / len(values)
        min_value = min(values)
        max_value = max(values)
        latest_value = values[-1]
        
        table_data.append({
            "metric": metric_name,
            "latest": f"{latest_value:.2f}",
            "avg": f"{avg_value:.2f}",
            "min": f"{min_value:.2f}",
            "max": f"{max_value:.2f}",
            "unit": metric_info["unit"],
            "points": str(len(points))
        })
    
    # Calculate column widths
    metric_width = max(len("Metric"), max(len(row["metric"]) for row in table_data))
    latest_width = max(len("Latest"), max(len(row["latest"]) for row in table_data))
    avg_width = max(len("Avg"), max(len(row["avg"]) for row in table_data))
    min_width = max(len("Min"), max(len(row["min"]) for row in table_data))
    max_width = max(len("Max"), max(len(row["max"]) for row in table_data))
    unit_width = max(len("Unit"), max(len(row["unit"]) for row in table_data))
    points_width = max(len("Points"), max(len(row["points"]) for row in table_data))
    
    # Create table
    header = f"| {'Metric':<{metric_width}} | {'Latest':<{latest_width}} | {'Avg':<{avg_width}} | {'Min':<{min_width}} | {'Max':<{max_width}} | {'Unit':<{unit_width}} | {'Points':<{points_width}} |"
    separator = f"|{'-' * (metric_width + 2)}|{'-' * (latest_width + 2)}|{'-' * (avg_width + 2)}|{'-' * (min_width + 2)}|{'-' * (max_width + 2)}|{'-' * (unit_width + 2)}|{'-' * (points_width + 2)}|"
    
    lines = [header, separator]
    for row in table_data:
        line = f"| {row['metric']:<{metric_width}} | {row['latest']:<{latest_width}} | {row['avg']:<{avg_width}} | {row['min']:<{min_width}} | {row['max']:<{max_width}} | {row['unit']:<{unit_width}} | {row['points']:<{points_width}} |"
        lines.append(line)
    
    return "\n".join(lines)


def format_metrics_timeseries(metrics: Dict[str, Dict[str, Any]], limit_points: int = 10) -> str:
    """Format metrics data showing time series points."""
    if not metrics:
        return "No metrics found."
    
    lines = []
    
    for metric_name, data in metrics.items():
        lines.append(f"\n📊 {metric_name}")
        lines.append("-" * (len(metric_name) + 4))
        
        if "error" in data:
            lines.append(f"❌ Error: {data['error']}")
            continue
        
        metric_info = extract_metrics_info(data)
        
        if metric_info["status"] == "no_data" or not metric_info["points"]:
            lines.append("⚠️  No data available")
            continue
        
        points = metric_info["points"]
        unit = metric_info["unit"]
        unit_str = f" {unit}" if unit else ""
        
        # Show recent points (limited)
        recent_points = points[-limit_points:] if len(points) > limit_points else points
        
        lines.append(f"Aggregation: {metric_info['aggr']}")
        lines.append(f"Scope: {metric_info['scope']}")
        lines.append(f"Recent {len(recent_points)} points:")
        
        for timestamp, value in recent_points:
            if value is not None:
                # Convert timestamp to readable format (Datadog uses milliseconds)
                import datetime
                dt = datetime.datetime.fromtimestamp(timestamp / 1000)
                time_str = dt.strftime("%H:%M:%S")
                lines.append(f"  {time_str}: {value:.2f}{unit_str}")

        lines.append("")

    return "\n".join(lines)


def extract_trace_info(trace_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract relevant information from trace events.

    Args:
        trace_events: List of trace event dictionaries from Datadog API

    Returns:
        List of processed trace dictionaries with extracted fields
    """
    from datetime import datetime

    traces = []

    for event in trace_events:
        attrs = event.get("attributes", {})

        # Calculate duration from timestamps if not provided directly
        duration_ns = attrs.get("duration", 0)
        if duration_ns == 0:
            start_ts = attrs.get("start_timestamp", "")
            end_ts = attrs.get("end_timestamp", "")
            if start_ts and end_ts:
                try:
                    start_dt = datetime.fromisoformat(start_ts.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_ts.replace('Z', '+00:00'))
                    duration_seconds = (end_dt - start_dt).total_seconds()
                    duration_ns = int(duration_seconds * 1_000_000_000)
                except (ValueError, AttributeError):
                    pass

        # Extract key fields
        trace = {
            "trace_id": attrs.get("trace_id", ""),
            "span_id": attrs.get("span_id", ""),
            "parent_id": attrs.get("parent_id"),
            "service": attrs.get("service", ""),
            "resource_name": attrs.get("resource_name", ""),
            "operation_name": attrs.get("operation_name", ""),
            "duration_ns": duration_ns,
            "duration_ms": round(duration_ns / 1_000_000, 2),
            "start_timestamp": attrs.get("start_timestamp", attrs.get("start", 0)),
            "status": attrs.get("status", ""),
            "error": attrs.get("error", 0),
            "env": attrs.get("env", ""),
            "tags": attrs.get("tags", []),
        }

        # Extract custom tags (@ prefixed attributes)
        custom_attrs = {}
        for key, value in attrs.items():
            if key.startswith("@"):
                custom_attrs[key] = value

        trace["custom_attributes"] = custom_attrs

        traces.append(trace)

    return traces


def format_traces_as_table(traces: List[Dict[str, Any]]) -> str:
    """Format traces as a text table.

    Args:
        traces: List of processed trace dictionaries

    Returns:
        Formatted table string
    """
    if not traces:
        return "No traces found"

    lines = []
    lines.append("SERVICE | RESOURCE | OPERATION | DURATION (ms) | STATUS | ENV")
    lines.append("-" * 100)

    for trace in traces:
        service = trace.get("service", "")[:20]
        resource = trace.get("resource_name", "")[:30]
        operation = trace.get("operation_name", "")[:20]
        duration = trace.get("duration_ms", 0)
        status = trace.get("status", "")
        env = trace.get("env", "")
        error_indicator = "❌" if trace.get("error") else ""

        lines.append(
            f"{service:<20} | {resource:<30} | {operation:<20} | {duration:>13.2f} | {status:<6} {error_indicator} | {env}"
        )

    return "\n".join(lines)


def format_traces_as_text(traces: List[Dict[str, Any]]) -> str:
    """Format traces as detailed text output.

    Args:
        traces: List of processed trace dictionaries

    Returns:
        Formatted text string
    """
    if not traces:
        return "No traces found"

    lines = []

    for i, trace in enumerate(traces, 1):
        lines.append(f"\n[{i}] {trace.get('service', 'unknown')} - {trace.get('resource_name', 'unknown')}")
        lines.append(f"    Trace ID: {trace.get('trace_id', '')}")
        lines.append(f"    Span ID: {trace.get('span_id', '')}")
        if trace.get("parent_id"):
            lines.append(f"    Parent ID: {trace.get('parent_id')}")
        lines.append(f"    Operation: {trace.get('operation_name', '')}")
        lines.append(f"    Duration: {trace.get('duration_ms', 0):.2f}ms")
        lines.append(f"    Status: {trace.get('status', '')} {'❌ ERROR' if trace.get('error') else ''}")
        lines.append(f"    Environment: {trace.get('env', '')}")

        # Show custom attributes if present
        custom_attrs = trace.get("custom_attributes", {})
        if custom_attrs:
            lines.append("    Custom Attributes:")
            for key, value in list(custom_attrs.items())[:5]:  # Limit to 5 attributes
                lines.append(f"      {key}: {value}")

    return "\n".join(lines)


def format_traces_as_hierarchy(traces: List[Dict[str, Any]]) -> str:
    """Format traces as a hierarchical tree structure showing parent-child relationships.

    Args:
        traces: List of processed trace dictionaries

    Returns:
        Formatted hierarchy string
    """
    if not traces:
        return "No traces found"

    # Build parent-child mapping
    trace_map = {trace["span_id"]: trace for trace in traces}
    root_traces = []
    children_map = {}

    for trace in traces:
        parent_id = trace.get("parent_id")
        if not parent_id or parent_id not in trace_map:
            root_traces.append(trace)
        else:
            if parent_id not in children_map:
                children_map[parent_id] = []
            children_map[parent_id].append(trace)

    def format_trace_node(trace: Dict[str, Any], indent: int = 0) -> List[str]:
        """Recursively format a trace and its children."""
        lines = []
        prefix = "  " * indent + ("└─ " if indent > 0 else "")

        duration = trace.get("duration_ms", 0)
        status = trace.get("status", "")
        error_indicator = "❌" if trace.get("error") else ""

        service = trace.get("service", "unknown")
        operation = trace.get("operation_name", "")
        resource = trace.get("resource_name", "")

        lines.append(
            f"{prefix}{service} - {operation} ({duration:.2f}ms) {status} {error_indicator}"
        )
        if resource and indent == 0:  # Only show resource for root spans
            lines.append(f"{'  ' * (indent + 1)}Resource: {resource}")

        # Add children
        span_id = trace["span_id"]
        if span_id in children_map:
            for child in children_map[span_id]:
                lines.extend(format_trace_node(child, indent + 1))

        return lines

    # Format all root traces
    all_lines = []
    for root in root_traces:
        all_lines.extend(format_trace_node(root))
        all_lines.append("")  # Blank line between traces

    return "\n".join(all_lines)