"""LangChain tool implementations for AI Lead Generation Agent.

All tools are decorated with @tool for direct use with LangChain AgentExecutor.
Re-exported here for convenient single-point imports.
"""

from tools.search_tool import search_companies, search_company_contacts
from tools.scrape_tool import scrape_website, scrape_company_about
from tools.company_info_tool import extract_company_info
from tools.contact_finder import find_contact_info

__all__ = [
    "search_companies",
    "search_company_contacts",
    "scrape_website",
    "scrape_company_about",
    "extract_company_info",
    "find_contact_info",
]

# Convenience list for agent tool binding
ALL_TOOLS = [
    search_companies,
    search_company_contacts,
    scrape_website,
    scrape_company_about,
    extract_company_info,
    find_contact_info,
]
