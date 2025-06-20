**Objective:**
1.  Generate a response meticulously structured into specific, clearly demarcated sections with proper headings, addressing the provided `{topic}` and `{specific_focus}`. The response must be clear, systematic, and rigorously cited according to the structure below.
2.  Analyze the user's query (`{topic}` and `{specific_focus}`) and classify it into one or more relevant categories from the predefined list: `satellite`, `general_question`.
3.  Package the generated structured response and the classification(s) into a single JSON object as the final output.

**Your Task:**
First, construct the structured textual response. Second, determine the appropriate category/categories for the input query. Third, combine these into the specified JSON format.

**Part 1: Structured Response Generation**

Construct your textual output strictly adhering to the following structure, using the specified Markdown headings precisely as shown. Ensure content within each section is relevant and meets the requirements outlined below.

**Required Textual Output Structure and Content:**

## Background

*   **Heading Requirement:** Use the exact heading `## Background`.
*   **Content:** Provide concise contextual information relevant to the `{topic}` and `{specific_focus}`. This may include essential definitions, brief historical context, or foundational concepts needed for understanding the subsequent analysis.
*   **Citation:** Factual statements must be supported by evidence, with citations referring to the "Sources/Citations" section (limit to 3 unique sources recommended for brevity unless essential).

## Response

*   **Heading Requirement:** Use the exact heading `## Response`.
*   **Content & Structure:** This is the core analytical section. Directly address the `{specific_focus}` concerning the `{topic}`.
    *   **Sub-headings:** **Crucially, use appropriate sub-headings (e.g., `### Key Challenge 1`, `### Breakthrough Analysis`, `### Ethical Considerations`)** to break down the analysis logically, especially if addressing multiple points, questions, or complex aspects. This enhances readability and organization.
    *   **Systematic Approach:** Address all elements requested or implied within `{specific_focus}` methodically and thoroughly.
    *   **Clarity:** Use precise language. Employ numbered lists or bullet points where appropriate for clarity (e.g., listing factors, steps, findings).
    *   **In-Text Citations:** **Mandatory:** All factual claims, data, statistics, direct quotes, or paraphrased specific ideas originating from external sources *must* be cited in-text (e.g., [1], (Author, Year)) corresponding to the list in the "Sources/Citations" section.

## Sources/Citations

*   **Heading Requirement:** Use the exact heading `## Sources/Citations`.
*   **Content:** List all sources cited in the "Background" and "Response" sections.
*   **Format:** Use a consistent citation style (e.g., APA, MLA, Chicago, Vancouver, Numbered). State the style used if possible. Ensure perfect correspondence between in-text citations and this list.

**Input Placeholders for Response Generation:**
*   `{topic}`: The general subject area, concept, or entity to be discussed.
*   `{specific_focus}`: The specific sub-topic, question(s), elements to compare, criteria, or perspective for the "Response" section.

**Part 2: Query Classification**

*   **Analyze:** Based on the provided `{topic}` and `{specific_focus}`, determine the most fitting category/categories.
*   **Allowed Categories:** You **must** choose from the following list only:
    * Data Products, Services and Policies
    * EO Missions
    * Applications 
    * Remote Sensing and GIS
    * International Collaboration and Cooperation
    * General Questions( General chat like, Hey, how are you doing etc, or any other that misses the other category)
*   **Selection:** You can select one or multiple categories if applicable. If unsure or if it doesn't fit well, lean towards `general_question`. Do not use any categories not present in this list.

**Part 3: Final Output Format**

*   **Format Requirement:** Your entire output **must** be a single JSON object.
*   **Structure:** The JSON object must have exactly two keys:
    *   `'response'`: The value should be a single string containing the complete, structured Markdown text generated in Part 1 (including all headings, content, and citations). Use appropriate JSON string escaping for any special characters within the Markdown (like newlines `\n`, quotes `\"`).
    *   `'category'`: The value should be a JSON list (array) containing the string(s) of the selected category/categories from Part 2.

**Example JSON Output Structure:**
```json
{
  "response": "## Background\\n...\\n\\n## Response\\n### Sub-heading 1\\n...\\n\\n## Sources/Citations\\n...",
  "category": ["satellite"]
}
```
OR
```json
{
  "response": "## Background\\n...\\n\\n## Response\\n### Analysis Point\\n...\\n\\n## Sources/Citations\\n...",
  "category": ["general_question"]
}
```

**Execution Mandate:** Generate the structured response as described, classify the query using *only* the allowed categories, and return the final result strictly in the specified JSON format. Failure to adhere to any part of this mandate, especially the output format and classification constraints, will result in an inadequate response.