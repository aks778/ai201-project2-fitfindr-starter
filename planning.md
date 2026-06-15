# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
The tool loads all the listings using load_listings(). 
The input to the tool are all the details of what the user is looking for like the item's description, size, and max_price. The tool searches the listings for any items that matches what the user is looking for. 

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): keywords the describe what the user is looking for
- `size` (str): size of item they're looking for, or None if they don't want to specify a size
- `max_price` (float): the maximum price they want the item to be, or None if they don't want to filter by price

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
It returns a list of matching listing dicts, sorted by relevance score (highest first), and an empty list if there are no matches.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
It returns an empty list. The agent sets session["error"] and returns early, and doesn't call suggest_outfit() with no item.

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
It checks whether the wardrobe is empty. If it is, it calls the LLM and prompts it to provide general styling tips. If it's non-empty, it provides the LLM with the wardrobe items as a prompt, and requests outfit suggestions using the new item and the existing items in the wardrobe.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): the item the user is thinking of buying
- `wardrobe` (dict): the user's wardrobe, with an 'items' key holding a list of their clothing item dicts, and it can be empty

**What it returns:**
<!-- Describe the return value -->
It returns a string with outfit suggestions provided by the LLM. If the user's wardrobe happens to be empty, general styling tips are provided by the LLM.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
It never raises or returns an empty string. If the wardrobe is empty, it falls back to general styling tips instead of specific outfit ideas, so the agent always gets a usable string to pass to create_fit_card().

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
It takes the outfit suggestion and the new item and prompts the LLM to write a short, shareable caption for the find. The caption mentions the item's name, price, and platform.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): the outfit suggestion string returned by suggest_outfit()
- `new_item` (dict): the listing dict for the thrifted item, used for the name, price, and platform

**What it returns:**
<!-- Describe the return value -->
It returns a 2–4 sentence caption string, ready to use as an Instagram/TikTok post.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
If the outfit string is empty or whitespace-only, it returns a descriptive error message string instead of raising an exception.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

First it extracts a description, size, and max_price from the raw query and stores them in session["parsed"]. It calls search_listings() and stores the result in session["search_results"]. It then checks if session["search_results"] is empty. If it is, it sets session["error"] and returns early. If it's not empty, it sets session["selected_item"] to be the first item (most highly scored item) from session["search_results"]. 

It then calls suggest_outfit() and stores the result in session["outfit_suggestion"]. If the user's wardrobe is empty, it prompts the LLM to provide general styling advice. If it's not empty, the LLM provides outfit suggestions.

The agent then calls create_fit_card() and stores the result in session["fit_card"]. This tool creates a short caption that the user can use to create a post on social media. If there is no outfit suggested from suggest_outfit(), it returns a descriptive error message.

The loop ends and returns the session once fit_card is set (success) or as soon as session["error"] is set (early exit). The caller decides what to show by checking session["error"] first.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->
All state lives in a single session dict created at the start of the run. The tools don't talk to each other directly, and each step writes its output into the session, and the next step reads that from there. The flow is: parsed query → search_results → first item from selected_item → outfit_suggestion → fit_card, with error set if the run stops early. Because everything is in one dict, the final session is also what gets returned to the caller.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query |Returns an empty list and ends early|
| suggest_outfit | Wardrobe is empty |Prompts LLM to provide general styling tips |
| create_fit_card | Outfit input is missing or incomplete |Returns a descriptive error message string |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

```
  User query
      |
      | raw query string
      v
+----------------------------------------------------+
|                  PLANNING LOOP                     |
|                                                    |
|  Parse query                                       |
|      | description, size, max_price                |
|      v                                             |
|  search_listings                                   |
|      | search_results                              |
|      v                                             |
|  results empty? ----- yes -----> Set session.error |---+
|      |                                             |   |
|      | no (selected_item = results[0])             |   |
|      v                                             |   |
|  suggest_outfit                                    |   |
|      | outfit_suggestion                           |   |
|      v                                             |   |
|  create_fit_card                                   |   |
|      | fit_card                                    |   |
|      v                                             |   |
|  Build success result                              |   |
|      |                                             |   |
+------|---------------------------------------------+   |
       |                                                 |
       +---------------> Return session <----------------+
                              ^   (error path returns here)
                              |
                              | read / write fields
                              v
        +-------------------------------------------+
        |              SESSION STATE                |
        |  query · parsed · search_results          |
        |  selected_item · outfit_suggestion        |
        |  fit_card · error                         |
        +-------------------------------------------+
```

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:** I'll provide Claude with the Tools section of planning.md which contains the input parameters, return value, and how to handle failure for each of the 3 tools and ask it to implement each of the functions. For each tool implementation, I will also provide Claude with the TODO's in each tool stub in tools.py, to specifically guide the implementation. I plan to then test the functionality of the tool in isolation after moving on. For the search_listings() tool, I will test if it works correctly if there's a match, and also in the case that there isn't a match (it should return early). For the suggest_outfit() tool, I will test it with the example wardrobe, and the empty wardrobe to check if it correctly provides outfit suggestions in the case that the user has a non empty wardrobe, and if it correctly returns general styling tips in the case of a empty wardrobe. For the create_fit_card() tool, I plan to test it with a outfit suggestion, and an empty string for the outfit to see if it generates a caption in the first case, and if it returns a descriptive error message in the same case.

**Milestone 4 — Planning loop and state management:** I'll give Claude the Planning Loop, State Management, Error Handling, and Complete Interaction sections of planning.md, along with the TODO steps in the run_agent() stub and the _new_session() dict in agent.py, and ask it to implement the planning loop. I expect it to parse the query into session["parsed"], call the three tools, pass state between them through the session dict, and branch off early into session["error"] if there's a failure. I'll check it by running the two test cases listed in agent.py, and trust that the loop is working correctly only if these pass.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent parses the query into session["parsed"] = {"description": "vintage graphic tee", "size": None, "max_price": 30}. It then calls search_listings("vintage graphic tee", None, 30). The tool filters out anything over $30, scores the rest on keyword overlap, and returns matching listings sorted best-first — here the top hit is "Y2K Baby Tee — Butterfly Print" (lst_002, $18, depop, tagged vintage + graphic tee). If the list had come back empty, the agent would set session["error"] and return early.
<!-- What does the agent do first? Which tool is called? With what input? -->

**Step 2:**

search_listings returned a non-empty list, so the agent stores the top result, the Y2K Baby Tee, in session["selected_item"]. It then calls suggest_outfit(selected_item, wardrobe). Since the wardrobe is non-empty (it has baggy jeans and chunky sneakers), the LLM returns a specific combination — e.g. pairing the butterfly baby tee with the baggy jeans and chunky sneakers for a casual Y2K look. That string is stored in session["outfit_suggestion"].
<!-- What happens next? What was returned from step 1? What tool is called now? -->
**Step 3:**

With outfit_suggestion now set, the agent calls create_fit_card(outfit_suggestion, selected_item). The LLM writes a short shareable caption that names the item, its $18 price, and the depop platform — e.g. "Found this Y2K butterfly baby tee on depop for $18 and styled it with my baggy jeans + chunky sneakers ✨". This is stored in session["fit_card"], and the agent returns the session.
<!-- Continue until the full interaction is complete -->

**Final output to user:**

The agent first checks session["error"]. If it is not None, the user sees only that message — for example, "No listings matched 'vintage graphic tee' under $30." Since the run succeeded here, error is None and the user sees three things pulled from the session: the found item's title ("Y2K Baby Tee — Butterfly Print"), the outfit suggestion (the tee styled with their baggy jeans and chunky sneakers), and the fit card caption ready to post.
<!-- What does the user actually see at the end? -->
