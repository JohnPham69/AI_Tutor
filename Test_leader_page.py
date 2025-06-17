import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials


# Call set_page_config as the first Streamlit command
"""Displays the leaderboard page."""
st.title("🏆 Leaderboard")

# Sample leaderboard data
data = [
    {"User Name": "Alice", "Percentage": 95, "School": "Northwood High", "Class": "11A", "Student ID": "NHS1001"},
    {"User Name": "Eve", "Percentage": 90, "School": "Southwood High", "Class": "11B", "Student ID": "SHS2002"},
    {"User Name": "Charlie", "Percentage": 80, "School": "Northwood High", "Class": "11A", "Student ID": "NHS1003"},
    {"User Name": "David", "Percentage": 75, "School": "Eastwood Academy", "Class": "11C", "Student ID": "EAS3004"},
    {"User Name": "Bob", "Percentage": 96, "School": "Westwood School", "Class": "11D", "Student ID": "WWS4005"},  # User to highlight
    {"User Name": "Fiona", "Percentage": 88, "School": "Northwood High", "Class": "11B", "Student ID": "NHS1006"},
    {"User Name": "George", "Percentage": 70, "School": "Southwood High", "Class": "11A", "Student ID": "SHS2007"},
    {"User Name": "Hannah", "Percentage": 92, "School": "Eastwood Academy", "Class": "11C", "Student ID": "EAS3008"},
    {"User Name": "Ian", "Percentage": 65, "School": "Westwood School", "Class": "11D", "Student ID": "WWS4009"},
    {"User Name": "Julia", "Percentage": 78, "School": "Northwood High", "Class": "11A", "Student ID": "NHS1010"},
]

df = pd.DataFrame(data)

# Sort by percentage in descending order and add Rank
df = df.sort_values(by="Percentage", ascending=False).reset_index(drop=True)
df.insert(0, 'Rank', range(1, 1 + len(df)))
df['Rank'] = df['Rank'].astype(str) # Convert Rank to string to prepend emoji

# Add medals to top 3
medals = ["🥇", "🥈", "🥉"]
for i in range(min(3, len(df))):
    df.loc[i, 'Rank'] = f"{medals[i]} {df.loc[i, 'Rank']}"

# Format Percentage column to include '%'
df['Percentage'] = df['Percentage'].astype(str) + '%'

def highlight_user(row):
    """Highlights a specific user in the DataFrame."""
    color_style = 'background-color: yellow; font-weight: bold;' if row['User Name'] == 'Bob' else ''
    return [color_style] * len(row)

st.subheader("Top Performers")
st.dataframe(df.style.apply(highlight_user, axis=1), hide_index=True, use_container_width=True)
