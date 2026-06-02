import os
import re
import unicodedata

import nltk
from bs4 import BeautifulSoup


def clean_text_for_tts(text):
    """
    Cleans text for TTS only. Visual text remains untouched.
    """
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'\.\s\.\s\.', '...', text)
    text = text.replace('—', ', ').replace('–', '-')
    text = re.sub(r'(?<=[a-zA-Z])[\u2018\u2019\u0027](?=[a-zA-Z])', '___APO___', text)
    text = re.sub(r'["“”‘’\']', '', text)
    text = text.replace('___APO___', "'")
    text = re.sub(r'[!]{2,}', '!', text)
    text = re.sub(r'[?]{2,}', '?', text)
    allowed = re.compile(r"[^a-zA-Z0-9\s.,?!;:'-]")
    text = allowed.sub("", text)
    return re.sub(r'\s+', ' ', text).strip()


def process_xhtml_inplace(filepath, global_id_start, css_rel_path):
    filename = os.path.basename(filepath)
    print(f"Processing: {filename}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'xml')

        # Cleanup & CSS
        for tag in soup.find_all("a"):
            if "noteref" in tag.get("class", []) or tag.get("role") == "doc-noteref": tag.decompose()

        head = soup.find('head')
        if head:
            css_name = os.path.basename(css_rel_path)
            if not any(css_name in l.get('href', '') for l in head.find_all('link')):
                head.append(soup.new_tag("link", rel="stylesheet", href=css_rel_path, type="text/css"))

        segments = []
        current_id = global_id_start
        block_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote', 'div']
        VOID_TAGS = {'br', 'img', 'hr', 'area', 'base', 'col', 'embed', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

        for tag in soup.find_all(block_tags):
            if tag.find(block_tags): continue

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
                    cursor_raw = len(full_text_raw) # Fallback
                split_indices.append(cursor_raw)

            # 2. Reconstruction
            new_html_content = ""
            current_sent_idx = 0
            current_char_count = 0

            seg_id = f"f{current_id:06d}"
            segments.append({"id": seg_id, "text": clean_text_for_tts(sentences_clean[0])})
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
                                seg_id = f"f{current_id:06d}"
                                current_id += 1
                                segments.append({"id": seg_id, "text": clean_text_for_tts(sentences_clean[current_sent_idx])})

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
                                seg_id = f"f{current_id:06d}"
                                current_id += 1
                                segments.append({"id": seg_id, "text": clean_text_for_tts(sentences_clean[current_sent_idx])})

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
        print(f"  [ERROR] Failed to process {filename}: {e}")
        return [], global_id_start

    with open(filepath, 'w', encoding='utf-8') as f:
        # Use str(soup) instead of prettify to prevent injecting unwanted whitespace
        f.write(str(soup))
    return segments, current_id
