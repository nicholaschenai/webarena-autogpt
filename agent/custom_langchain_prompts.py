import json

MAIN_PREFIX = """You are an autonomous intelligent agent tasked with completing an objective via navigating a web browser.
    This objective will be accomplished through the use of specific actions (tools/commands) you can issue.

    Here's the information you'll have:
    The user's objective: This is the task you're trying to complete.
    The current web page's accessibility tree: This is a simplified representation of the webpage, providing key information. 
    The accessibility tree is of the form `[element_id] Text describing the element` (i.e. the element id is to the left of the description)
    The current web page's URL: This is the page you're currently navigating.
    The open tabs: These are the tabs you have open, of the form `Tab [tab_index]: Title of tab (current) | Tab 1: ..` where the `(current)` signifies the tab you are on and the tabs are delimited by `|`. 
    """



HOMEPAGE_PROMPT = f"""

    Homepage:
    If you want to visit other websites, check out the homepage at http://homepage.com. It has a list of websites you can visit.

    """

RULES_PROMPT = """
To be successful, it is very important to follow the following rules:
1. You should only issue an action that is valid given the current observation (most RECENT observation returned by the system). Do not engage with element ids from the examples or from messages in the past as they might be invalid.
2. In your thoughts, you should follow the examples to reason step by step and then issue the next action.
3. Think whether your action makes sense. For example, it is pointless to click on static texts as it does nothing.
4. Issue stop action when you think you have achieved the objective.
"""

example_a = {
            "thoughts": {
                "text": "I think I have achieved the objective.",
                "reasoning": "Let's think step-by-step. This page lists the information of HP Inkjet Fax Machine, which is the product identified in the objective. Its price is $279.49.",
                "plan": "- I will issue the stop action with the answer.",
                "criticism": ""
            },
            "command": {"name": "stop", "args": {"final_answer": "$279.49"}},
        }

example_b = {
            "thoughts": {
                "text": "I should use type_into_field",
                "reasoning": "Let's think step-by-step. This page has a search box whose ID is [164]. According to the nominatim rule of openstreetmap, I can search for the restaurants near a location by \"restaurants near\". I can submit my typing by pressing the Enter afterwards.",
                "plan": "- Use type_into_field to search for restaurants nearby and press Enter afterwards",
                "criticism": ""
            },
            "command": {"name": "type_into_field", "args": {"element_id": 164, "content": "restaurants near CMU", "press_enter_after": 1}},
        }


AUTOGPT_EXAMPLE_PROMPT = f"""
=====Start of example 1 =====
GOALS:
1. #### Accomplish this goal in 30 actions. What is the price of HP Inkjet Fax Machine

=Observation=
URL: http://onestopmarket.com/office-products/office-electronics.html
Accessibility tree:
[1744] link 'HP CB782A#ABA 640 Inkjet Fax Machine (Renewed)'
        [1749] StaticText '$279.49'
        [1757] button 'Add to Cart'
        [1760] button 'Add to Wish List'
        [1761] button 'Add to Compare'

Response:
{json.dumps(example_a, indent=4)}

=====End of example 1 =====

=====Start of example 2 =====
GOALS:
1. #### Accomplish this goal in 30 actions. Show me the restaurants near CMU

=Observation=
URL: http://openstreetmap.org
Accessibility tree:
[164] textbox 'Search' focused: True required: False
[171] button 'Go'
[174] link 'Find directions between two points'
[212] heading 'Search Results'
[216] button 'Close'

Response:
{json.dumps(example_b, indent=4)}

=====End of example 2 =====
"""
