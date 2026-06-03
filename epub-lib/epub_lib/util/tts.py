import logging
import re
import unicodedata
from typing import Tuple, List

import nltk
from bs4 import BeautifulSoup

from epub_lib.model.tts import Fragment, FragmentList, TextFragment

LOG = logging.getLogger(__name__)


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

def fid(frag_id: int) -> str:
    return f"nn{frag_id}"

def process_xhtml_inplace(file_bytes: bytes, global_id_start) -> Tuple[bytes, FragmentList, int]:
    try:
        soup = BeautifulSoup(file_bytes, 'xml')

        # Cleanup links
        for tag in soup.find_all("a"):
            if "noteref" in tag.get("class", []) or tag.get("role") == "doc-noteref":
                LOG.warning("Removing link: %s", tag)
                tag.decompose()

        fragments: List[Fragment] = []
        current_id = global_id_start
        block_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote', 'div']
        VOID_TAGS = {'br', 'img', 'hr', 'area', 'base', 'col', 'embed', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

        for tag in soup.find_all(block_tags):
            if tag.find(block_tags): continue

            full_text_raw = tag.get_text()
            if not full_text_raw.strip(): continue
            LOG.debug("Raw text:\n%s", full_text_raw)

            # TODO: Add punctuation to raw text, if it does not end with one.
            # TODO: Only send to split, if it's too long.
            # TODO: Catch pauses here.
            # TODO: Do guessing if it's an acronym or simply all caps... Lower if latter.

            # Clean for NLTK
            full_text_clean = re.sub(r'\s+', ' ', full_text_raw).strip()
            sentences_clean = nltk.sent_tokenize(full_text_clean)
            if not sentences_clean: continue

            LOG.debug("NLTK sent_tokenize result:\n%s", sentences_clean)

            # TODO: tweak split here. < Should I do it here or before NLTK?
            # TODO: Further split too long sentences.
            # TODO: Merge too short sentences.

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
                    cursor_raw = len(full_text_raw) # Fallback
                split_indices.append(cursor_raw)

            # 2. Reconstruction
            new_html_content = ""
            current_sent_idx = 0
            current_char_count = 0

            seg_id = fid(current_id)
            fragments.append(TextFragment(id=seg_id, text=clean_text_for_tts(sentences_clean[0])))
            current_id += 1

            new_html_content += f'<span id="{seg_id}">'

            def traverse(node, open_tags):
                nonlocal new_html_content, current_char_count, current_sent_idx, current_id

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
                                seg_id = fid(current_id)
                                current_id += 1
                                fragments.append(TextFragment(id=seg_id, text=clean_text_for_tts(sentences_clean[current_sent_idx])))

                                new_html_content += f'<span id="{seg_id}">'
                                for t_name, t_attrs in open_tags:
                                    attr_str = " ".join([f'{k}="{v}"' for k,v in t_attrs.items()])
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
                                seg_id = fid(current_id)
                                current_id += 1
                                fragments.append(TextFragment(id=seg_id, text=clean_text_for_tts(sentences_clean[current_sent_idx])))

                                new_html_content += f'<span id="{seg_id}">'
                                for t_name, t_attrs in open_tags:
                                    attr_str = " ".join([f'{k}="{v}"' for k,v in t_attrs.items()])
                                    new_html_content += f"<{t_name} {attr_str}>" if attr_str else f"<{t_name}>"

                            text = text[remaining_len:]

                elif node.name:
                    attrs = {k: " ".join(v) if isinstance(v, list) else v for k, v in node.attrs.items()}
                    attr_str = " ".join([f'{k}="{v}"' for k,v in attrs.items()])
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

    # TODO: Split fragments into tracks of roughly the same length ~3-5min.

    return soup.encode(formatter="minimal", encoding='utf-8'), FragmentList(fragments), current_id
