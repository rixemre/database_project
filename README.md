# Week 1 – Data Collection Phase

During the first week, we focused on preparing the data collection infrastructure for the Bannerlord Database project.
A Python virtual environment was created, and the project structure was organized into scrape/, data/, and sql/ directories.
We implemented a basic web scraper using the Fandom (MediaWiki) API to retrieve HTML content for individual Lord pages.
The scraper parses infobox details (name, age, gender, level) and extracts traits and skill data sections.

Sample data was collected for three Lords (Caladog, Lucon, Rhagaea) and stored in CSV format (lords.csv, lord_traits.csv, lord_skills.csv).
SQL DDL files defining the lords, lord_traits, and lord_skills tables were also drafted.

This week’s goal was to establish the foundation for automated data gathering, which will later be imported into the relational database.