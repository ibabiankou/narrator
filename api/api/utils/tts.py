import logging
import nltk
import re
import unicodedata
from bs4 import BeautifulSoup, Tag
from typing import Tuple, List

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


def split_into_fragments(tag: Tag, target_length: int = 75) -> List[List[Token]]:
    raw_text = tag.get_text()
    tokens = [Token(t) for t in tokenize_with_whitespace(raw_text)]

    # Split tokens into fragments.
    fragments = []
    total_len = sum([t.length for t in tokens])
    num_fragments = max(1, round(total_len / target_length))
    avg_len = total_len / num_fragments
    remaining_len = avg_len
    current_fragment: List[Token] = []
    for token in tokens:
        if remaining_len <=0:
            fragments.append(current_fragment)
            current_fragment = []
            remaining_len += avg_len

        current_fragment.append(token)
        remaining_len -= token.length
    if current_fragment:
        fragments.append(current_fragment)

    LOG.info("\n%s\n%s\n%s\n%s", tag, raw_text, [t.normalized_text for t in tokens], fragments)

    return fragments

# A screenshot of her message app popped up. It was a conversation between
# her and Morrigan. Most of it was cut off, and she’d just snapped the last exchange.

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
VOID_TAGS = {'br', 'img', 'hr', 'area', 'base', 'col', 'embed', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

def process_xhtml_inplace(file_bytes: bytes, global_id_start) -> Tuple[bytes, FragmentList, int]:
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

            split_into_fragments(tag)
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
                    while len(text) > 0:
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

                    if node.name in VOID_TAGS:
                        new_html_content += tag_open.replace(">", " />")
                    else:
                        open_tags.append((node.name, attrs))
                        new_html_content += tag_open
                        for child in node.contents:
                            traverse(child, open_tags)
                        new_html_content += f"</{node.name}>"
                        open_tags.pop()

            for child in tag.contents:
                traverse(child, [])

            new_html_content += "</span>"

            wrapped_content = f"<body>{new_html_content}</body>"
            new_soup = BeautifulSoup(wrapped_content, 'xml')
            tag.clear()
            if new_soup.body:
                for child in list(new_soup.body.contents): tag.append(child)

    except Exception as e:
        LOG.error("Failed to fragment the content: %s", e, exc_info=True)
        raise e

    return soup.encode(formatter="minimal", encoding='utf-8'), fragments.build(), fragments.current_id
