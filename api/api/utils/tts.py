from collections import deque

import logging
import nltk
import re
import unicodedata
from bs4 import BeautifulSoup, Tag
from typing import Tuple, List, Set, Optional

from common_lib.models.tts import FragmentList, FragmentListBuilder, Token

LOG = logging.getLogger(__name__)


# class Quotes(LineTransformer):
#     pairs = {
#         "“": "\"",
#         "”": "\"",
#         "«": "\"",
#         "»": "\"",
#         "‹": "'",
#         "›": "'",
#         "‘": "'",
#         "’": "'",
#     }
#
#     def __call__(self, line: str) -> str:
#         for key, value in self.pairs.items():
#             line = line.replace(key, value)
#         return line


def clean_text_for_tts(text):
    """
    Cleans text for TTS only. Visual text remains untouched.
    """
    # TODO Ensure apostrophe in height measuremenets are not removed. Or replaced with words.
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'\.\s*\.\s*\.', '...', text)
    text = text.replace('—', ', ').replace('–', '-')
    text = re.sub(r'(?<=[a-zA-Z])[\u2018\u2019\u0027](?=[a-zA-Z])', '___APO___', text)
    text = re.sub(r'["“”‘’\']', '', text)
    text = text.replace('___APO___', "'")
    text = re.sub(r'[!]{2,}', '!', text)
    text = re.sub(r'[?]{2,}', '?', text)
    allowed = re.compile(r"[^a-zA-Z0-9\s.,?!;:'-]")
    text = allowed.sub("", text)
    return re.sub(r'\s+', ' ', text).strip()


def new_span(id: str) -> str:
    return f'<span id="{id}" class="nf">'


# Regex to split a string into tokens on whitespace without loosing anything.
TOKEN_PATTERN = re.compile(r'\S+\s*|\s+')


def tokenize_with_whitespace(text: str) -> List[str]:
    """
    Split the result string into tokens on whitespace characters, preserving all whitespace characters.
    Each token is a word plus all whitespace characters. Joining all tokens without any separators
    should reconstruct the original string.
    """
    return TOKEN_PATTERN.findall(text)


BLOCK_TAGS = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote', 'div', 'table', 'th', 'td'}
VOID_TAGS = {'br', 'img', 'hr', 'area', 'base', 'col', 'embed', 'input', 'link', 'meta', 'param', 'source', 'track',
             'wbr'}


def process_xhtml_inplace(file_bytes: bytes, global_id_start) -> Tuple[bytes, FragmentList, int]:
    LOG.debug("V1 Start...")
    try:
        soup = BeautifulSoup(file_bytes, 'xml')

        # Cleanup links
        for tag in soup.find_all("a"):
            if "noteref" in tag.get("class", []) or tag.get("role") == "doc-noteref":
                LOG.warning("Removing link: %s", tag)
                tag.decompose()

        fragments = FragmentListBuilder(current_id=global_id_start)

        visited_ids = set()
        for tag in soup.find_all():
            if tag.get("id"):
                tag_id: str = str(tag.get("id"))
                visited_ids.add(tag_id)

            if tag.name not in BLOCK_TAGS: continue
            if tag.find(BLOCK_TAGS): continue

            full_text_raw = tag.get_text()
            if not full_text_raw.strip(): continue

            # Clean for NLTK
            full_text_clean = re.sub(r'\s+', ' ', full_text_raw).strip()
            sentences_clean = nltk.sent_tokenize(full_text_clean)
            if not sentences_clean: continue

            # 1. Fuzzy Boundary Calc
            split_indices = []
            cursor_raw = 0
            for i, sent_clean in enumerate(sentences_clean):
                safe_sent = re.escape(sent_clean)
                pattern_str = safe_sent.replace(r'\ ', r'\s+')
                pattern = re.compile(pattern_str)
                match = pattern.search(full_text_raw, cursor_raw)

                if match:
                    end_raw = match.end()
                    while end_raw < len(full_text_raw) and full_text_raw[end_raw].isspace():
                        end_raw += 1
                    cursor_raw = end_raw
                else:
                    cursor_raw = len(full_text_raw)  # Fallback
                split_indices.append(cursor_raw)

            # 2. Reconstruction
            new_html_content = ""
            current_sent_idx = 0
            current_char_count = 0

            frag = fragments.add_text(clean_text_for_tts(sentences_clean[current_sent_idx]), list(visited_ids))
            seg_id = frag.formatted_id()

            new_html_content += new_span(seg_id)

            def traverse(node, open_tags):
                nonlocal new_html_content, current_char_count, current_sent_idx

                if isinstance(node, str):
                    text = str(node)

                    LOG.debug("  " * len(open_tags) + "Node is a string, so processing it...")

                    while len(text) > 0:
                        LOG.debug("  " * len(open_tags) + "Remaining text: %s", text)

                        if current_sent_idx >= len(split_indices):
                            new_html_content += text
                            current_char_count += len(text)
                            break

                        boundary = split_indices[current_sent_idx]
                        remaining_len = boundary - current_char_count

                        # --- THE FIX IS HERE ---
                        # If we have reached (or passed) the boundary exactly at the end of this node,
                        # we must TRIGGER THE SPLIT logic to register the next sentence.

                        if remaining_len <= 0:
                            # Exact match or drift

                            # Close current
                            for t_name, _ in reversed(open_tags): new_html_content += f"</{t_name}>"
                            new_html_content += "</span>"

                            # Increment Index
                            current_sent_idx += 1

                            # Start Next (if exists)
                            if current_sent_idx < len(sentences_clean):
                                frag = fragments.add_text(clean_text_for_tts(
                                    sentences_clean[current_sent_idx]), list(visited_ids))
                                seg_id = frag.formatted_id()

                                new_html_content += new_span(seg_id)
                                # TODO: If any of the tags have ID, it would be now duplicated.
                                for t_name, t_attrs in open_tags:
                                    attr_str = " ".join([f'{k}="{v}"' for k, v in t_attrs.items()])
                                    new_html_content += f"<{t_name} {attr_str}>" if attr_str else f"<{t_name}>"

                            # Note: We do NOT consume text here because remaining_len was 0.
                            # We just perform the state switch and loop again to process the text
                            # (which now belongs to the new sentence) or exit if text is empty.
                            continue

                        # Normal Processing
                        if len(text) <= remaining_len:
                            new_html_content += text
                            current_char_count += len(text)
                            break
                        else:
                            # Split in middle of node
                            chunk = text[:remaining_len]
                            new_html_content += chunk
                            current_char_count += len(chunk)

                            for t_name, _ in reversed(open_tags): new_html_content += f"</{t_name}>"
                            new_html_content += "</span>"

                            current_sent_idx += 1
                            if current_sent_idx < len(sentences_clean):
                                frag = fragments.add_text(clean_text_for_tts(
                                    sentences_clean[current_sent_idx]), list(visited_ids))
                                seg_id = frag.formatted_id()

                                new_html_content += new_span(seg_id)
                                for t_name, t_attrs in open_tags:
                                    attr_str = " ".join([f'{k}="{v}"' for k, v in t_attrs.items()])
                                    new_html_content += f"<{t_name} {attr_str}>" if attr_str else f"<{t_name}>"

                            text = text[remaining_len:]

                elif node.name:
                    attrs = {k: " ".join(v) if isinstance(v, list) else v for k, v in node.attrs.items()}
                    attr_str = " ".join([f'{k}="{v}"' for k, v in attrs.items()])
                    tag_open = f"<{node.name} {attr_str}>" if attr_str else f"<{node.name}>"

                    LOG.debug("  " * len(open_tags) + "Traversing: %s", node.name)

                    if node.name in VOID_TAGS:
                        new_html_content += tag_open.replace(">", " />")
                    else:
                        # Open if needed
                        open_tags.append((node.name, attrs))
                        new_html_content += tag_open
                        for child in node.contents:
                            traverse(child, open_tags)
                        new_html_content += f"</{node.name}>"
                        open_tags.pop()
                        LOG.debug("  " * len(open_tags) + "Exiting: %s", node.name)

                else:
                    LOG.warning("  " * len(open_tags) + "  >>> Not a string and has no name: %s", node)
                    raise RuntimeError("Unexpected node type")

            for child in tag.contents:
                traverse(child, [])

            new_html_content += "</span>"

            # TODO: The following part is weird as fuck! I wonder if I can build beautiful soup model right away
            #  and avoid entire string concatenation and parsing shenanigans.
            wrapped_content = f"<body>{new_html_content}</body>"
            new_soup = BeautifulSoup(wrapped_content, 'xml')
            tag.clear()
            if new_soup.body:
                for child in list(new_soup.body.contents): tag.append(child)

    except Exception as e:
        LOG.error("Failed to fragment the content: %s", e, exc_info=True)
        raise e

    LOG.debug("V1 END...")
    return soup.encode(formatter="minimal", encoding='utf-8'), fragments.build(), fragments.current_id


def tokenize_tag_content(tag: Tag) -> List[Token]:
    all_tokens = []

    def traverse(node):
        """Do an in-order depth-first traversal of the tag tree. Tokenize each string node."""
        if isinstance(node, str):
            node_tokens = [Token(t) for t in tokenize_with_whitespace(node)]
            all_tokens.extend(node_tokens)
        elif node.name:
            for child in node.contents:
                traverse(child)

    traverse(tag)
    return all_tokens


def split_tokens_into_fragments(tokens: List[Token], target_length: int = 75) -> List[List[Token]]:
    if not tokens: return []

    fragments = []
    total_len = sum([t.length for t in tokens])
    num_fragments = max(1, round(total_len / target_length))
    avg_len = total_len / num_fragments

    remaining_len = avg_len
    current_fragment: List[Token] = []
    for token in tokens:
        if remaining_len <= 0:
            # Only split fragments where there is whitespace between edge elements.
            if current_fragment[-1].ends_with_whitespace() or token.starts_with_whitespace():
                fragments.append(current_fragment)
                current_fragment = []
                remaining_len += avg_len

        current_fragment.append(token)
        remaining_len -= token.length
    if current_fragment:
        fragments.append(current_fragment)
    return fragments


class FragmentInjector:
    # The fragment markup is always at the root level of the tag.

    def __init__(self,
                 tag: Tag,
                 fragments: FragmentListBuilder,
                 visited_ids: Optional[Set[str]]= None,
                 target_length: int = 75):
        # Updated content of the tag to be concatenated.
        self.new_content = ["<body>"]

        self.tag = tag
        self.fragments = fragments
        self.target_length = target_length

        # TODO: make sure to push / pop IDs encountered during tag traversal.
        self.visited_ids = visited_ids or set()

        # Unprocessed tokens in the current fragment.
        self.frag_q = deque[Token]()
        # Unprocessed tokens in the current tag.
        self.tag_q = deque[Token]()

        self.pending_fragments: deque[List[Token]] = deque()
        self.current_fragment = None

        self.open_tag_stack = []

    def inject(self):
        # Split the content into fragments.
        tag_tokens = tokenize_tag_content(self.tag)
        if not tag_tokens: return

        self.pending_fragments.extend(split_tokens_into_fragments(tag_tokens, target_length=self.target_length))

        for child in self.tag.contents:
            self.traverse(child)
        self.new_content.append(f"</span>")

        # TODO: The following part is weird as fuck! I wonder if I can build beautiful soup model right away
        #  and avoid entire string concatenation and parsing shenanigans.
        self.new_content.append("</body>")
        new_soup = BeautifulSoup("".join(self.new_content), 'xml')
        self.tag.clear()
        if new_soup.body:
            for child in list(new_soup.body.contents): self.tag.append(child)

        return self.tag

    def open_fragment_if_needed(self):
        if len(self.frag_q) == 0 and len(self.pending_fragments) > 0:
            next_fragment = self.pending_fragments.popleft()
            self.frag_q.extend(next_fragment)

            # Close the current fragment, if present
            if self.current_fragment is not None:
                for t_name, _ in reversed(self.open_tag_stack):
                    self.new_content.append(f"</{t_name}>")
                self.new_content.append(f"</span>")

            added_fragment = self.fragments.add_text("".join([t.tts_text for t in next_fragment]), list(self.visited_ids))
            self.current_fragment = added_fragment

            # Open newly added fragment and re-open all tags.
            self.new_content.append(new_span(added_fragment.formatted_id()))
            for t_name, t_attrs in self.open_tag_stack:
                attr_str = " ".join([f'{k}="{v}"' for k, v in t_attrs.items()])
                self.new_content.append(f"<{t_name} {attr_str}>" if attr_str else f"<{t_name}>")

    def traverse(self, node):
        self.open_fragment_if_needed()

        if isinstance(node, str):
            node_tokens = [Token(t) for t in tokenize_with_whitespace(node)]
            self.tag_q.extend(node_tokens)

            while len(self.tag_q) > 0:
                tag_tok = self.tag_q.popleft()
                frag_tok = self.frag_q.popleft()
                if tag_tok.normalized_text != frag_tok.normalized_text:
                    # This should not be happening, because both fragments and these tokens are collected the same way.
                    raise ValueError(f"Token mismatch: '{tag_tok}' != '{frag_tok}'")

                self.new_content.append(tag_tok.raw_text)

                if len(self.frag_q) == 0 and len(self.tag_q) > 0:
                    # End of the fragment is reached, but we have more content here, so open another one.
                    self.open_fragment_if_needed()

        elif node.name: # TODO: figure out where name is added and do a nicer check to keep the type info.
            # Current node is a tag node, open in and add to the open_tag_stack

            attrs = {k: " ".join(v) if isinstance(v, list) else v for k, v in node.attrs.items()}
            attr_str = " ".join([f'{k}="{v}"' for k, v in attrs.items()])
            tag_open = f"<{node.name} {attr_str}>" if attr_str else f"<{node.name}>"

            LOG.debug("  " * len(self.open_tag_stack) + "Traversing: %s", node.name)

            if node.name in VOID_TAGS:
                self.new_content.append(tag_open.replace(">", " />"))
            else:
                self.open_tag_stack.append((node.name, attrs))
                self.new_content.append(tag_open)
                for child in node.contents:
                    # If the current fragment queue is empty, then open the next fragment.
                    self.traverse(child)
                self.new_content.append(f"</{node.name}>")
                self.open_tag_stack.pop()
        else:
            LOG.warning("  " * len(self.open_tag_stack) + "  >>> Not a string and has no name: %s", node)
            raise RuntimeError("Unexpected node type")


def fragment_tag_content(tag: Tag, fragments: FragmentListBuilder, visited_ids: Set[str]) -> Optional[str]:
    tag_tokens = tokenize_tag_content(tag)
    planned_fragments: List[List[Token]] = split_tokens_into_fragments(tag_tokens)
    if not planned_fragments: return None

    # Inject fragment boundaries.
    new_html_content = ""
    current_fragment_idx = 0

    # Unprocessed tokens in the current fragment.
    frag_q = deque[Token]()
    # Unprocessed tokens in the current tag.
    tag_q = deque[Token]()

    current_fragment = planned_fragments[current_fragment_idx]
    frag_q.extend(current_fragment)
    frag = fragments.add_text("".join([t.tts_text for t in current_fragment]), list(visited_ids))
    seg_id = frag.formatted_id()

    new_html_content += new_span(seg_id)

    def traverse(node, open_tags):
        nonlocal new_html_content, current_fragment_idx

        if isinstance(node, str):
            text = str(node)

            # Split text into tokens.
            tokens = [Token(t) for t in tokenize_with_whitespace(text)]
            tag_q.extend(tokens)

            LOG.debug("  " * len(open_tags) + "Node is a string, so processing it...")
            LOG.debug("  " * len(open_tags) + "\nnode tokens: %s\nsent tokens: %s\nopen tags: %s", tag_q,
                      frag_q, open_tags)

            # Iterate over both tokens and current "sentence";
            # If run out of sentence tokens, inject the span tags.
            # If run out of text tokens, return and wait for the next tag.

            # 1. tag has more tokens than sentence.

            while len(tag_q) > 0:  # Handle all tokens in the current tag.
                if len(frag_q) == 0:
                    # A new sentence is needed. So pick it up.
                    LOG.debug("  " * len(
                        open_tags) + "Reached end of sentence. Closing span and taking next sentence.")

                    # Close current fragment
                    for t_name, _ in reversed(open_tags): new_html_content += f"</{t_name}>"
                    new_html_content += "</span>"

                    # Take next sentence.
                    current_fragment_idx += 1

                    # Start Next fragment (if sentence exists)
                    if current_fragment_idx < len(planned_fragments):
                        sentence_tokens = planned_fragments[current_fragment_idx]
                        frag_q.extend(sentence_tokens)
                        frag = fragments.add_text("".join([t.tts_text for t in sentence_tokens]),
                                                  list(visited_ids))
                        seg_id = frag.formatted_id()

                        new_html_content += new_span(seg_id)
                        # TODO: If any of the tags have ID, it would be now duplicated.
                        for t_name, t_attrs in open_tags:
                            attr_str = " ".join([f'{k}="{v}"' for k, v in t_attrs.items()])
                            new_html_content += f"<{t_name} {attr_str}>" if attr_str else f"<{t_name}>"
                    else:
                        if len(tag_q) > 0:
                            raise ValueError("Tag has more tokens, but no more sentences!")

                tag_tok = tag_q.popleft()
                sent_tok = frag_q.popleft()
                if tag_tok.normalized_text != sent_tok.normalized_text:
                    raise ValueError(f"Token mismatch: '{tag_tok}' != '{sent_tok}'")

                new_html_content += tag_tok.raw_text

                if len(frag_q) == 0 and len(tag_q) == 0:
                    LOG.debug(
                        "  " * len(open_tags) + "Reached end of sentence and tag together. Breaking cycle.")
                    break

                if len(frag_q) == 0:  # Reached end of the sentence/fragment, so close, take next, continue.
                    LOG.debug("  " * len(
                        open_tags) + "Reached end of sentence. Closing span and taking next sentence.")

                    # Close current fragment
                    for t_name, _ in reversed(open_tags): new_html_content += f"</{t_name}>"
                    new_html_content += "</span>"

                    # Take next sentence.
                    current_fragment_idx += 1

                    # Start Next fragment (if sentence exists)
                    if current_fragment_idx < len(planned_fragments):
                        sentence_tokens = planned_fragments[current_fragment_idx]
                        frag_q.extend(sentence_tokens)
                        frag = fragments.add_text("".join([t.tts_text for t in sentence_tokens]),
                                                  list(visited_ids))
                        seg_id = frag.formatted_id()

                        new_html_content += new_span(seg_id)
                        # TODO: If any of the tags have ID, it would be now duplicated.
                        for t_name, t_attrs in open_tags:
                            attr_str = " ".join([f'{k}="{v}"' for k, v in t_attrs.items()])
                            new_html_content += f"<{t_name} {attr_str}>" if attr_str else f"<{t_name}>"
                    else:
                        if len(tag_q) > 0:
                            raise ValueError("Tag has more tokens, but no more sentences!")

        elif node.name:
            attrs = {k: " ".join(v) if isinstance(v, list) else v for k, v in node.attrs.items()}
            attr_str = " ".join([f'{k}="{v}"' for k, v in attrs.items()])
            tag_open = f"<{node.name} {attr_str}>" if attr_str else f"<{node.name}>"

            LOG.debug("  " * len(open_tags) + "Traversing: %s", node.name)

            if node.name in VOID_TAGS:
                new_html_content += tag_open.replace(">", " />")
            else:
                open_tags.append((node.name, attrs))
                new_html_content += tag_open
                for child in node.contents:
                    traverse(child, open_tags)
                new_html_content += f"</{node.name}>"
                open_tags.pop()
                LOG.debug("  " * len(open_tags) + "Exiting: %s", node.name)

        else:
            LOG.warning("  " * len(open_tags) + "  >>> Not a string and has no name: %s", node)
            raise RuntimeError("Unexpected node type")

    for child in tag.contents:
        traverse(child, [])

    new_html_content += "</span>"
    return new_html_content


def process_xhtml_inplace_v2(file_bytes: bytes, global_id_start) -> Tuple[bytes, FragmentList, int]:
    LOG.debug("V2 Start...")
    try:
        soup = BeautifulSoup(file_bytes, 'xml')

        fragments = FragmentListBuilder(current_id=global_id_start)

        visited_ids = set()
        for tag in soup.find_all():
            if tag.get("id"):
                tag_id: str = str(tag.get("id"))
                visited_ids.add(tag_id)

            if tag.name not in BLOCK_TAGS: continue
            if tag.find(BLOCK_TAGS): continue

            injector = FragmentInjector(tag, fragments, visited_ids)
            injector.inject()

    except Exception as e:
        LOG.error("Failed to fragment the content: %s", e, exc_info=True)
        raise e

    LOG.debug("V2 END...")
    return soup.encode(formatter="minimal", encoding='utf-8'), fragments.build(), fragments.current_id
