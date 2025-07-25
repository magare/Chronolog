from typing import Dict, List, Optional, Tuple
from datetime import datetime
import math


class RepositoryVisualizer:
    """Creates text-based visualizations for repository analytics in TUI."""
    
    @staticmethod
    def create_bar_chart(data: Dict[str, float], width: int = 50, 
                        height: int = 10, title: Optional[str] = None) -> str:
        """Create a horizontal bar chart."""
        if not data:
            return "No data to display"
        
        lines = []
        if title:
            lines.append(title)
            lines.append("-" * width)
        
        max_value = max(data.values()) if data else 1
        max_label_len = max(len(str(k)) for k in data.keys()) if data else 0
        
        for label, value in data.items():
            bar_width = int((value / max_value) * (width - max_label_len - 10))
            bar = "█" * bar_width
            percentage = (value / max_value) * 100
            
            line = f"{label:<{max_label_len}} │ {bar} {value:.1f} ({percentage:.1f}%)"
            lines.append(line)
        
        return "\n".join(lines)
    
    @staticmethod
    def create_line_chart(data: List[float], width: int = 60, 
                         height: int = 15, title: Optional[str] = None) -> str:
        """Create a simple line chart using Unicode characters."""
        if not data:
            return "No data to display"
        
        lines = []
        if title:
            lines.append(title)
            lines.append("-" * width)
        
        max_val = max(data) if data else 1
        min_val = min(data) if data else 0
        value_range = max_val - min_val if max_val != min_val else 1
        
        # Create the chart grid
        chart = []
        for h in range(height):
            row = []
            for w in range(width):
                row.append(" ")
            chart.append(row)
        
        # Plot the data points
        if len(data) > 1:
            x_scale = (width - 1) / (len(data) - 1)
            
            for i, value in enumerate(data):
                x = int(i * x_scale)
                y = height - 1 - int(((value - min_val) / value_range) * (height - 1))
                
                if 0 <= x < width and 0 <= y < height:
                    chart[y][x] = "●"
                
                # Draw lines between points
                if i > 0:
                    prev_value = data[i-1]
                    prev_x = int((i-1) * x_scale)
                    prev_y = height - 1 - int(((prev_value - min_val) / value_range) * (height - 1))
                    
                    # Simple line drawing
                    steps = max(abs(x - prev_x), abs(y - prev_y))
                    if steps > 0:
                        for step in range(1, steps):
                            interp_x = prev_x + (x - prev_x) * step // steps
                            interp_y = prev_y + (y - prev_y) * step // steps
                            if 0 <= interp_x < width and 0 <= interp_y < height:
                                if chart[interp_y][interp_x] == " ":
                                    chart[interp_y][interp_x] = "·"
        
        # Add Y-axis labels
        for i in range(0, height, max(1, height // 5)):
            y_value = max_val - (i / (height - 1)) * value_range
            y_label = f"{y_value:6.1f}"
            lines.append(f"{y_label} │ {''.join(chart[i])}")
        
        # Add X-axis
        lines.append("       └" + "─" * width)
        
        return "\n".join(lines)
    
    @staticmethod
    def create_heatmap(data: List[List[float]], width: int = 50, 
                      height: int = 10, title: Optional[str] = None) -> str:
        """Create a heatmap using Unicode block characters."""
        if not data or not data[0]:
            return "No data to display"
        
        lines = []
        if title:
            lines.append(title)
            lines.append("-" * width)
        
        # Intensity characters from light to dark
        intensity_chars = " ·░▒▓█"
        
        # Flatten data to find min/max
        flat_data = [val for row in data for val in row]
        max_val = max(flat_data) if flat_data else 1
        min_val = min(flat_data) if flat_data else 0
        value_range = max_val - min_val if max_val != min_val else 1
        
        # Create heatmap
        for row in data:
            line = ""
            for value in row:
                intensity = (value - min_val) / value_range
                char_index = int(intensity * (len(intensity_chars) - 1))
                line += intensity_chars[char_index] * 2  # Double width for better visibility
            lines.append(line)
        
        return "\n".join(lines)
    
    @staticmethod
    def create_sparkline(data: List[float], width: int = 20) -> str:
        """Create a compact sparkline chart."""
        if not data:
            return ""
        
        # Sparkline characters
        spark_chars = "▁▂▃▄▅▆▇█"
        
        max_val = max(data)
        min_val = min(data)
        value_range = max_val - min_val if max_val != min_val else 1
        
        # Sample data if too long
        if len(data) > width:
            step = len(data) / width
            sampled_data = []
            for i in range(width):
                index = int(i * step)
                sampled_data.append(data[index])
            data = sampled_data
        
        sparkline = ""
        for value in data:
            intensity = (value - min_val) / value_range
            char_index = int(intensity * (len(spark_chars) - 1))
            sparkline += spark_chars[char_index]
        
        return sparkline
    
    @staticmethod
    def create_tree_map(data: Dict[str, float], width: int = 60, 
                       height: int = 20) -> str:
        """Create a simple tree map visualization."""
        if not data:
            return "No data to display"
        
        # Sort by value
        sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
        total = sum(data.values())
        
        lines = []
        current_y = 0
        
        for label, value in sorted_items:
            if current_y >= height:
                break
            
            # Calculate rectangle height based on value
            rect_height = max(1, int((value / total) * height))
            if current_y + rect_height > height:
                rect_height = height - current_y
            
            # Create rectangle
            for i in range(rect_height):
                if i == rect_height // 2:
                    # Center label in rectangle
                    content = f" {label[:width-4]} ({value:.0f}) "
                    padding = width - len(content)
                    line = "█" + content + "█" * max(0, padding - 1)
                else:
                    line = "█" * width
                lines.append(line[:width])
            
            current_y += rect_height
        
        return "\n".join(lines)
    
    @staticmethod
    def create_progress_bar(current: float, total: float, width: int = 40,
                           label: Optional[str] = None) -> str:
        """Create a progress bar."""
        if total == 0:
            percentage = 0
        else:
            percentage = (current / total) * 100
        
        filled_width = int((current / total) * width) if total > 0 else 0
        bar = "█" * filled_width + "░" * (width - filled_width)
        
        if label:
            return f"{label}: [{bar}] {percentage:.1f}% ({current:.0f}/{total:.0f})"
        else:
            return f"[{bar}] {percentage:.1f}%"
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    @staticmethod
    def create_activity_calendar(daily_data: List[int], weeks: int = 12) -> str:
        """Create a GitHub-style activity calendar."""
        if not daily_data:
            return "No data to display"
        
        # Intensity characters
        intensity_chars = " ·░▒▓█"
        
        # Get max value for normalization
        max_val = max(daily_data) if daily_data else 1
        
        # Days of week labels
        dow_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        lines = []
        lines.append("    " + " ".join(f"W{i+1:2d}" for i in range(0, min(weeks, len(daily_data)//7), 2)))
        
        # Create calendar grid
        for dow in range(7):
            line = f"{dow_labels[dow]} "
            
            for week in range(weeks):
                day_index = week * 7 + dow
                if day_index < len(daily_data):
                    value = daily_data[day_index]
                    intensity = value / max_val if max_val > 0 else 0
                    char_index = int(intensity * (len(intensity_chars) - 1))
                    line += intensity_chars[char_index] + " "
                else:
                    line += "  "
            
            lines.append(line)
        
        return "\n".join(lines)