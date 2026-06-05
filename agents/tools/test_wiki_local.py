from agents.tools.wiki_tools import wikipedia_search

result = wikipedia_search.invoke({"title": "Alien", "year": 1979})

print(result)