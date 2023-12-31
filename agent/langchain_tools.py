"""
implement the actions as tools so we can validate inputs

Notes:

- on parsing differences b/w langchain and this implementation
langchain uses output_parse.parse, which decides if it matches a tool or response["action"] == "Final Answer"
which sets off the agentfinish sequence. In the prompt they put "Final Answer" as an avail choice

this mod: remove Final Answer from prompt. 'stop' action has return_action=True so it terminates upon that
but possible for agent to accidentally say "Final Answer" to early terminate, might need to edit output_parser if
this becomes an issue
"""

import json
import langchain

from langchain.schema.output import LLMResult

from langchain.agents import AgentType, initialize_agent

from langchain.tools import Tool, StructuredTool
from langchain.tools.base import ToolException

from langchain.chat_models import ChatOpenAI
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chains.llm import LLMChain

from langchain.vectorstores import FAISS
from langchain.docstore import InMemoryDocstore
from langchain.embeddings import OpenAIEmbeddings

# Initialize the vectorstore as empty
import faiss

from typing import Optional, List, Mapping, Any, Dict
# from pydantic import BaseModel, Field, root_validator
# from pydantic import Field, root_validator
# from pydantic.v1 import BaseModel, Field, root_validator
# from pydantic.v1 import BaseModel

from .autogpt import AutoGPT
from .custom_langchain_prompts import MAIN_PREFIX, HOMEPAGE_PROMPT, RULES_PROMPT

from browser_env.actions import (
    Action,
    ActionParsingError,
    create_id_based_action,
    create_none_action,
    create_playwright_action,
)

from browser_env import (
    Action,
    ActionTypes,
    ScriptBrowserEnv,
    StateInfo,
    Trajectory,
    create_stop_action,
)

from browser_env.helper_functions import (
    RenderHelper,
    get_action_description,
)

from browser_env.env_config import URL_MAPPINGS

import my_globals

from .autogpt_output_parser import (
    AutoGPTOutputParser,
    BaseAutoGPTOutputParser,
)
from .autogpt_prompt import AutoGPTPrompt

# Define your embedding model
embeddings_model = OpenAIEmbeddings()


def init_auto_agent(ai_name, ai_role, tools, input_variables, llm, vectorstore, max_tokens, init_obs=None, verbose=True,
                    top_k=1,
                    random=True, loop_limit=20, send_token_limit=4097, base_plus_mem_tokens=2500):
    prompt = AutoGPTPrompt(
        ai_name=ai_name,
        ai_role=ai_role,
        tools=tools,
        input_variables=input_variables,
        token_counter=llm.get_num_tokens,
        max_tokens=max_tokens,
        send_token_limit=send_token_limit,
        base_plus_mem_tokens=base_plus_mem_tokens
    )
    chain = LLMChain(llm=llm, prompt=prompt)

    agent = AutoGPT(
        ai_name=ai_name,
        memory=vectorstore.as_retriever(),
        chain=chain,
        output_parser=AutoGPTOutputParser(),
        tools=tools,
        loop_limit=loop_limit,
        init_obs=init_obs,
        top_k=top_k,
        random=random
    )
    agent.chain.verbose = verbose
    return agent


def init_vectorstore(embedding_size=1536):
    index = faiss.IndexFlatL2(embedding_size)
    vectorstore = FAISS(embeddings_model.embed_query, index, InMemoryDocstore({}), {})
    return vectorstore


class LLMOutputHandler(BaseCallbackHandler):
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        """Run when LLM ends running."""
        # do this to pass LLM outputs to render_helper. cos the intermediate_steps alr
        # uses output_parser which throws away raw LLM output
        my_globals.llm_response = response.generations[-1][0].text


def init_tools_args(args, lm_config, tokenizer):
    langchain.verbose = True
    RETURN_OBS_PREFIX = ""
    if args.lc_type == "autogpt":
        RETURN_OBS_PREFIX = "=Observation="

    PREV_ACTION_PROMPT = "The previous action: This is the action you just performed. It may be helpful to track your progress."

    ZERO_SHOT_REACT_PREFIX_END = """
    Respond to the human as helpfully and accurately as possible.
    You have access to the following tools:
    """

    PREFIX = MAIN_PREFIX + PREV_ACTION_PROMPT + HOMEPAGE_PROMPT + ZERO_SHOT_REACT_PREFIX_END

    EXAMPLE_PROMPT = """
    =====Start of example 1 =====
    YOUR CURRENT OBJECTIVE: What is the price of HP Inkjet Fax Machine
    PREVIOUS ACTION: None
    Observation:
    URL: http://onestopmarket.com/office-products/office-electronics.html
    Accessibility tree:
    [1744] link 'HP CB782A#ABA 640 Inkjet Fax Machine (Renewed)'
            [1749] StaticText '$279.49'
            [1757] button 'Add to Cart'
            [1760] button 'Add to Wish List'
            [1761] button 'Add to Compare'

    Thought: Let's think step-by-step. This page list the information of HP Inkjet Fax Machine, which is the product identified in the objective. Its price is $279.49. I think I have achieved the objective. I will issue the stop action with the answer.
    Action:
    ```
    {{
      "action": "stop",
      "action_input": {{"final_answer" : "$279.49"}}
    }}
    ```
    =====End of example 1 =====
    
    =====Start of example 2 =====
    YOUR CURRENT OBJECTIVE: Show me the restaurants near CMU
    PREVIOUS ACTION: None
    Observation:
    URL: http://openstreetmap.org
    Accessibility tree:
    [164] textbox 'Search' focused: True required: False
    [171] button 'Go'
    [174] link 'Find directions between two points'
    [212] heading 'Search Results'
    [216] button 'Close'
    Thought: Let's think step-by-step. This page has a search box whose ID is [164]. According to the nominatim rule of openstreetmap, I can search for the restaurants near a location by \"restaurants near\". I can submit my typing by pressing the Enter afterwards.
    Action:
    ```
    {{
      "action": "type_into_field",
      "action_input": {{"element_id": 164, content: "restaurants near CMU", press_enter_after: 1}}
    }}
    ```
    =====End of example 2 =====
    
    """

    ZERO_SHOT_REACT_SUFFIX_END = """
    Begin! Reminder to ALWAYS respond with a valid json blob of a single action.
    """

    SUFFIX = EXAMPLE_PROMPT + RULES_PROMPT + ZERO_SHOT_REACT_SUFFIX_END

    # REMOVE scratchpad for context limit. leave variable there for validation but display 0 chars
    # try memory variables or sth?
    HUMAN_MESSAGE_TEMPLATE = '{input}\n\n{agent_scratchpad:0.0}'
    # HUMAN_MESSAGE_TEMPLATE = '{input}\n\n{agent_scratchpad:0.0\n{tags}}'

    FORMAT_INSTRUCTIONS = """Use a json blob to specify a tool by providing an action key (tool name) and an action_input key (tool input).
    
    Valid "action" values: {tool_names}
    
    Provide only ONE action per $JSON_BLOB, as shown:
    
    ```
    {{{{
      "action": $TOOL_NAME,
      "action_input": $INPUT
    }}}}
    ```
        
    Follow this format:
    
    Thought: consider previous and subsequent steps, reason step by step what the best next action should be
    Action:
    ```
    $JSON_BLOB
    ```
    Observation: action result / accessibility tree / URL
    ... (repeat Thought/Action/Observation N times)
    Thought: The objective can be achieved now (and explain step by step why this is so). I know what to respond. 
    Action:
    ```
    {{{{
      "action": "stop",
      "action_input": {{{{"final_answer" : "Final response to human"}}}}
    }}}}
    ```"""

    a_kwargs = {
        'prefix': PREFIX,
        'format_instructions': FORMAT_INSTRUCTIONS,
        'suffix': SUFFIX,
        'human_message_template': HUMAN_MESSAGE_TEMPLATE,
    }

    ex1 = """
    Example:
    ### Example start ###
    Observation:
    [1744] link 'HP CB782A#ABA 640 Inkjet Fax Machine (Renewed)'
            [1749] StaticText '$279.49'
            [1757] button 'Add to Cart'
            
    In this example, there is a link with element id 1744 and a button with element id 1757. If you want to click on element
    id 1757, issue this function with 1757 as the parameter. Note that element 1749 is static text so it is not clickable
    ### Example end ###
    """

    ex2 = """
    Example:
    ### Example start ###
    Observation:
    [1744] link 'HP CB782A#ABA 640 Inkjet Fax Machine (Renewed)'
            [1749] StaticText '$279.49'
            [1757] button 'Add to Cart'
    
    OBJECTIVE: What is the price of HP Inkjet Fax Machine
    
    In this example we see that this page lists the information of HP Inkjet Fax Machine, which is the product identified in the objective. Its price is $279.49. Since you have achieved the objective, you will issue the stop action with the parameter $279.49
    ### Example end ###
    """

    def map_url_to_real(url: str) -> str:
        """Map the urls to their real world counterparts"""
        for i, j in URL_MAPPINGS.items():
            if i in url:
                url = url.replace(i, j)
        return url

    def map_url_to_local(url: str) -> str:
        """Map the urls to their local counterparts"""
        for i, j in URL_MAPPINGS.items():
            if j in url:
                url = url.replace(j, i)
            # https
            if j.replace("http", "https") in url:
                url = url.replace(j.replace("http", "https"), i)
        return url

    def create_action_from_str(parsed_response):
        # TODO: allow for playwright actions
        try:
            action = create_id_based_action(parsed_response)
        except ActionParsingError as e:
            action = create_none_action()
        action["raw_prediction"] = my_globals.llm_response

        return action

    def create_append_action(issued_action_str):
        action = create_action_from_str(issued_action_str)
        print(f'action: {action}')

        my_globals.trajectory.append(action)

        action_str = get_action_description(
            action,
            my_globals.state_info["info"]["observation_metadata"],
            action_set_tag=args.action_set_tag,
            prompt_constructor=None,
        )
        print(f'action str: {action_str}')
        my_globals.render_helper.render(
            action, my_globals.state_info, my_globals.meta_data, args.render_screenshot
        )
        my_globals.meta_data["action_history"].append(action_str)

        return action

    def execute_action(issued_action_str):
        # TODO: early stop, action error handling

        action = create_append_action(issued_action_str)

        # Note: this is meant to break loop if agent issues stop or early stopping
        # Since our agent's stop already breaks out of loop, we only need to
        # handle early stopping later
        # if action["action_type"] == ActionTypes.STOP:
        #     return STOP_SEQUENCE

        obs, _, terminated, _, info = my_globals.env.step(action)
        my_globals.state_info = {"observation": obs, "info": info}
        my_globals.trajectory.append(my_globals.state_info)

        # Note: the ScriptBrowserEnv always returns False for terminated
        # if terminated:
        #     my_globals.trajectory.append(create_stop_action(""))
        #     return STOP_SEQUENCE

        accessibility_tree = obs["text"]
        max_obs_length = lm_config.gen_config["max_obs_length"]
        if max_obs_length:
            accessibility_tree = tokenizer.decode(tokenizer.encode(accessibility_tree)[:max_obs_length])

        page = info["page"]
        url = page.url
        url = map_url_to_real(url)

        return RETURN_OBS_PREFIX + f"\n URL: \n {url} \n Accessibility tree: \n {accessibility_tree} \n"

    def _handle_error(error: ToolException) -> str:
        return (
                my_globals.tool_error_start
                + str(error.args[0])
                + " Please try other valid input(s) or tools."
        )

    def validate_element_id(fn_name: str, element_id: int):
        if str(element_id) not in my_globals.state_info['info']['observation_metadata']['text']['obs_nodes_info']:
            raise ToolException(f"Attempted to use tool {fn_name} on invalid element_id {element_id}\n"
                                f"The available element ids are {my_globals.state_info['info']['observation_metadata']['text']['obs_nodes_info'].keys()}"
                                )

    # class ElementToolInputSchema(BaseModel):
    #     element_id: int = Field()

    # @root_validator(skip_on_failure=True)
    # def validate_query(cls, values: Dict[str, Any]) -> Dict:
    #     element_id = values["element_id"]
    #     if str(element_id) not in my_globals.state_info['info']['observation_metadata']['text']['obs_nodes_info']:
    #         raise ToolException(
    #             f"Element id {element_id} is not available for current observation\n"
    #             f"The available element ids are {my_globals.state_info['info']['observation_metadata']['text']['obs_nodes_info'].keys()}"
    #         )
    #     return values

    def click(element_id: int):
        validate_element_id('click', element_id)
        return execute_action(f"click [{element_id}]")

    click_tool = StructuredTool.from_function(
        name="click",
        func=click,
        description="This action clicks on an element specified by the element_id in the input.",
        return_direct=args.tools_return_true,
        # args_schema=ElementToolInputSchema,
        handle_tool_error=_handle_error,
    )

    STOP_TOOL_DESC = """Issue this action when you believe the task is complete. If the objective is to find a text-based answer, provide the answer as an input to this tool. If you believe the task is impossible to complete, provide the answer as "N/A" as the input to this tool."""

    def stop(final_answer: Optional[str] = ''):
        action_str = f"stop [{final_answer}]"
        action = create_append_action(action_str)
        return action_str

    stop_tool = StructuredTool.from_function(
        name="stop",
        func=stop,
        description=STOP_TOOL_DESC,
        return_direct=True,
    )

    # class TypeToolInputSchema(BaseModel):
    #     element_id: int = Field()
    #     content: str = Field()
    #     press_enter_after: int = Field()
    #
    #     @root_validator(skip_on_failure=True)
    #     def validate_query(cls, values: Dict[str, Any]) -> Dict:
    #         element_id = values["element_id"]
    #         press_enter_after = values["press_enter_after"]
    #         if str(element_id) not in my_globals.state_info['info']['observation_metadata']['text']['obs_nodes_info']:
    #             raise ToolException(
    #                 f"Element id {element_id} is not available for current observation\n"
    #                 f"The available element ids are {my_globals.state_info['info']['observation_metadata']['text']['obs_nodes_info'].keys()}"
    #             )
    #         if press_enter_after not in [1, 0]:
    #             raise ToolException(
    #                 f"press_enter_after value {press_enter_after} is not valid. It should be 1 or 0."
    #             )
    #         return values

    TYPE_TOOL_DESC = """Use this to type the content into the field with element_id. press_enter_after is either 1 or 0. By default, the "Enter" key is pressed after typing unless press_enter_after is set to 0."""

    def validate_press_enter(fn_name: str, press_enter_after: int):
        if press_enter_after not in [1, 0]:
            raise ToolException(
                f"Attempted to use tool {fn_name} on invalid press_enter_after value {press_enter_after}. It should be 1 or 0."
            )

    def type_into_field(element_id: int, content: str, press_enter_after: Optional[int] = 1):
        validate_element_id('type_into_field', element_id)
        validate_press_enter('type_into_field', press_enter_after)
        return execute_action(f"type [{element_id}] [{content}] [{press_enter_after}]")

    type_tool = StructuredTool.from_function(
        name="type_into_field",
        func=type_into_field,
        description=TYPE_TOOL_DESC,
        return_direct=args.tools_return_true,
        # args_schema=TypeToolInputSchema,
        handle_tool_error=_handle_error,
    )

    def hover(element_id: int):
        validate_element_id('hover', element_id)
        return execute_action(f"hover [{element_id}]")

    hover_tool = StructuredTool.from_function(
        name="hover",
        func=hover,
        description="Hover over an element with element_id.",
        return_direct=args.tools_return_true,
        # args_schema=ElementToolInputSchema,
        handle_tool_error=_handle_error,
    )

    def press(key_comb: str):
        # TODO: consider validation for this
        return execute_action(f"press [{key_comb}]")

    press_tool = StructuredTool.from_function(
        name="press",
        func=press,
        description="Simulates the pressing of a key combination on the keyboard (e.g., Ctrl+v).",
        return_direct=args.tools_return_true,
    )

    # class ScrollToolInputSchema(BaseModel):
    #     direction: str = Field()
    #
    #     @root_validator(skip_on_failure=True)
    #     def validate_query(cls, values: Dict[str, Any]) -> Dict:
    #         direction = values["direction"]
    #         if direction not in ["up", "down"]:
    #             raise ToolException(
    #                 f"direction {direction} is not valid. It should be up or down"
    #             )
    #         return values

    def validate_scroll(fn_name: str, direction: str):
        if direction not in ["up", "down"]:
            raise ToolException(
                f"Attempted to use tool {fn_name} on invalid direction {direction}. It should be up or down."
            )

    def scroll(direction: str):
        validate_scroll('scroll', direction)
        return execute_action(f"scroll [{direction}]")

    scroll_tool = StructuredTool.from_function(
        name="scroll",
        func=scroll,
        description="Scroll the page. Specify the direction (up or down) in the input",
        return_direct=args.tools_return_true,
        # args_schema=ScrollToolInputSchema,
        handle_tool_error=_handle_error,
    )

    def new_tab():
        return execute_action("new_tab")

    new_tab_tool = StructuredTool.from_function(
        name="new_tab",
        func=new_tab,
        description="Open a new, empty browser tab",
        return_direct=args.tools_return_true,
    )

    # class TabFocusToolInputSchema(BaseModel):
    #     tab_index: int = Field()
    #
    #     @root_validator(skip_on_failure=True)
    #     def validate_query(cls, values: Dict[str, Any]) -> Dict:
    #         tab_index = values["tab_index"]
    #         tab_title_str, content = my_globals.state_info['observation'].split('\n\n')
    #         tabs = tab_title_str.split(" | ")
    #
    #         if tab_index not in range(len(tabs)):
    #             raise ToolException(
    #                 f"tab_index {tab_index} is not valid"
    #                 f"The available tab_index are {list(range(len(tabs)))}"
    #             )
    #         return values

    def validate_tab_focus(fn_name: str, tab_index: int):
        tab_title_str, content = my_globals.state_info['observation'].split('\n\n')
        tabs = tab_title_str.split(" | ")

        if tab_index not in range(len(tabs)):
            raise ToolException(
                f"Attempted to use tool {fn_name} on invalid tab_index {tab_index}."
                f"The available tab_index are {list(range(len(tabs)))}"
            )

    def tab_focus(tab_index: int):
        validate_tab_focus('tab_focus', tab_index)
        return execute_action(f"tab_focus [{tab_index}]")

    tab_focus_tool = StructuredTool.from_function(
        name="tab_focus",
        func=tab_focus,
        description="Switch the browser's focus to a specific tab using its index",
        return_direct=args.tools_return_true,
        # args_schema=TabFocusToolInputSchema,
        handle_tool_error=_handle_error,
    )

    def close_tab():
        return execute_action("close_tab")

    close_tab_tool = StructuredTool.from_function(
        name="close_tab",
        func=close_tab,
        description="Close the currently active tab.",
        return_direct=args.tools_return_true,
    )

    def go_back():
        return execute_action("go_back")

    go_back_tool = StructuredTool.from_function(
        name="go_back",
        func=go_back,
        description="Navigate to the previously viewed page.",
        return_direct=args.tools_return_true,
    )

    def go_forward():
        return execute_action("go_forward")

    go_forward_tool = StructuredTool.from_function(
        name="go_forward",
        func=go_forward,
        description="Navigate to the next page (if a previous 'go_back' action was performed).",
        return_direct=args.tools_return_true,
    )

    _APPROVED_DOMAINS = set([url.replace('http://', '') for url in URL_MAPPINGS.values()])
    _APPROVED_DOMAINS.update(['docs.gitlab.com', 'experienceleague.adobe.com'])
    print(f'approved domains: {_APPROVED_DOMAINS} \n')

    # class GotoToolInputSchema(BaseModel):
    #     url: str = Field()
    #
    #     @root_validator(skip_on_failure=True)
    #     def validate_query(cls, values: Dict[str, Any]) -> Dict:
    #         url = values["url"]
    #         for approved_domain in _APPROVED_DOMAINS:
    #             if approved_domain in url:
    #                 return values
    #
    #         raise ToolException(
    #             f"url {url} is not valid\n"
    #             f"The valid urls must contain any of {_APPROVED_DOMAINS}"
    #         )

    def validate_url(fn_name: str, url: str):
        for approved_domain in _APPROVED_DOMAINS:
            if approved_domain in url:
                return

        raise ToolException(
            f"Attempted to use tool {fn_name} on invalid url {url}\n"
            f"The valid urls must contain any of {_APPROVED_DOMAINS}"
        )

    def goto(url: str):
        validate_url('goto', url)
        return execute_action(f"goto [{map_url_to_local(url)}]")

    goto_tool = StructuredTool.from_function(
        name="goto",
        func=goto,
        description="Navigate to a specific URL.",
        return_direct=args.tools_return_true,
        # args_schema=GotoToolInputSchema,
        handle_tool_error=_handle_error,
    )

    return [stop_tool, click_tool, type_tool, hover_tool, press_tool, scroll_tool, new_tab_tool, tab_focus_tool,
            close_tab_tool, go_back_tool, go_forward_tool, goto_tool], a_kwargs

    # return [click_tool], a_kwargs


def init_agent(args, lm_config, tokenizer):
    tools, agent_kwargs = init_tools_args(args, lm_config, tokenizer)
    handler = LLMOutputHandler()
    if args.lc_type == "default":
        # Do not override stop_token as the zero shot react agent uses 'Observation'
        llm = ChatOpenAI(temperature=lm_config.gen_config["temperature"],
                         model_name=lm_config.model,
                         callbacks=[handler],
                         top_p=lm_config.gen_config["top_p"],
                         max_tokens=lm_config.gen_config["max_tokens"],
                         )

        def _handle_parsing_error(error) -> str:
            msg = my_globals.parse_error_start + str(error)
            return msg

        agent_chain = initialize_agent(tools, llm, agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                                       verbose=True, max_iterations=args.max_steps, agent_kwargs=agent_kwargs,
                                       handle_parsing_errors=_handle_parsing_error)
    elif args.lc_type == "autogpt":
        llm = ChatOpenAI(temperature=0.01,
                                model_name=lm_config.model,
                                callbacks=[handler],
                                max_tokens=lm_config.gen_config["max_tokens"])

        agent_chain = init_auto_agent(ai_name="Web Agent AI", ai_role="Web Agent", tools=tools,
                                      input_variables=["memory", "messages", "goals", "user_input"], llm=llm,
                                      vectorstore=init_vectorstore(), verbose=True, loop_limit=args.max_steps,
                                      max_tokens=lm_config.gen_config["max_tokens"],
                                      send_token_limit=args.send_token_limit,
                                      base_plus_mem_tokens=args.base_plus_mem_tokens)
    return agent_chain
