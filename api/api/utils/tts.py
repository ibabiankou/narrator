from collections import deque, defaultdict

import logging
import re
from bs4 import BeautifulSoup, Tag
from typing import Tuple, List, Set, Optional

from common_lib.models.tts import FragmentGroups, FragmentGroupsBuilder, Token

LOG = logging.getLogger(__name__)


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
ENSURE_PUNCTUATION = {'br'}


def tokenize_tag_content(tag: Tag) -> List[Token]:
    all_tokens: List[Token] = []

    def traverse(node):
        """Do an in-order depth-first traversal of the tag tree. Tokenize each string node."""
        if isinstance(node, str):
            node_tokens = [Token(t) for t in tokenize_with_whitespace(node)]
            all_tokens.extend(node_tokens)
        elif node.name:
            if node.name in ENSURE_PUNCTUATION and len(all_tokens) > 0:
                all_tokens[-1].add_punctuation_in_tts = True

            for child in node.contents:
                traverse(child)

    traverse(tag)
    return all_tokens


def split_tokens_into_fragments(tokens: List[Token], target_length: int = 75) -> List[List[Token]]:
    if not tokens: return []

    fragments = []
    total_len = sum([t.length for t in tokens])
    num_fragments = max(1, round(total_len / target_length))
    if num_fragments == 1: return [tokens]

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
                 fragments: FragmentGroupsBuilder,
                 visited_ids: Optional[Set[str]] = None,
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
        if self.only_empty(tag_tokens):
            return

        if tag_tokens:
            # Assuming that injection only happens on block elements such as paragraph or div.
            # Therefore, we want to ensure punctuation is present at the end to have an appropriate pause.
            tag_tokens[-1].add_punctuation_in_tts = True

        self.fragments.next_group()

        if self._scene_break(tag_tokens):
            self.fragments.add_pause(1, [])
            return

        self.pending_fragments.extend(split_tokens_into_fragments(tag_tokens, target_length=self.target_length))
        expected_fragment_number = len(self.pending_fragments)

        for child in self.tag.contents:
            self.traverse(child)
        self.new_content.append(f"</span>")

        # Temporary sanity check if the number of fragments in the current group matches the number of pending fragments
        actual_fragment_number = self.fragments.current_group_size()
        if actual_fragment_number != expected_fragment_number:
            LOG.warning("Expected %d fragments, but got %d", expected_fragment_number, actual_fragment_number)

        # TODO: The following part is weird as fuck! I wonder if I can build beautiful soup model right away
        #  and avoid entire string concatenation and parsing shenanigans.
        self.new_content.append("</body>")
        new_soup = BeautifulSoup("".join(self.new_content), 'xml')
        self.tag.clear()
        if new_soup.body:
            for child in list(new_soup.body.contents): self.tag.append(child)

    def only_empty(self, tokens: List[Token]):
        for t in tokens:
            if not t._tts_text.isspace():
                return False
        return True

    @staticmethod
    def _scene_break(tokens: List[Token]):
        """Returns True if we consider tokens to represent a scene break.
        Usually it's a number of repetitive non-word characters."""
        char_dict = defaultdict[str, int](int)
        total_count = 0
        for t in tokens:
            for c in t.raw_text:
                if c.isspace(): continue
                char_dict[c] += 1
                total_count += 1
        # Check if all the characters are non word characters.
        if len(char_dict) > 0 and total_count > 0:
            for character, count in char_dict.items():
                if character.isalnum():
                    return False
            return True
        return False

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

        elif node.name:  # TODO: figure out where name is added and do a nicer check to keep the type info.
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

    def open_fragment_if_needed(self):
        if len(self.frag_q) == 0 and len(self.pending_fragments) > 0:
            next_fragment = self.pending_fragments.popleft()
            self.frag_q.extend(next_fragment)

            # Close the current fragment, if present
            if self.current_fragment is not None:
                for t_name, _ in reversed(self.open_tag_stack):
                    self.new_content.append(f"</{t_name}>")
                self.new_content.append(f"</span>")

            added_fragment = self.fragments.add_tokens(next_fragment, list(self.visited_ids))
            self.current_fragment = added_fragment

            # Open newly added fragment and re-open all tags.
            self.new_content.append(new_span(added_fragment.formatted_id()))
            for t_name, t_attrs in self.open_tag_stack:
                attr_str = " ".join([f'{k}="{v}"' for k, v in t_attrs.items()])
                self.new_content.append(f"<{t_name} {attr_str}>" if attr_str else f"<{t_name}>")


def process_xhtml_inplace(file_bytes: bytes, global_id_start) -> Tuple[bytes, FragmentGroups, int]:
    try:
        soup = BeautifulSoup(file_bytes, 'xml')

        fragments = FragmentGroupsBuilder(current_id=global_id_start)

        visited_ids = set()
        for tag in soup.find_all():
            if tag.get("id"):
                tag_id: str = str(tag.get("id"))
                visited_ids.add(tag_id)

            if tag.name not in BLOCK_TAGS: continue
            if tag.find(BLOCK_TAGS): continue

            # TODO: This is where a fragment group (paragraph) starts.
            injector = FragmentInjector(tag, fragments, visited_ids)
            injector.inject()

    except Exception as e:
        LOG.error("Failed to fragment the content: %s", e, exc_info=True)
        raise e

    return soup.encode(formatter="minimal", encoding='utf-8'), fragments.build(), fragments.current_id
