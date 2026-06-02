import logging

from epub_lib.util.tts import process_xhtml_inplace

LOG = logging.getLogger(__name__)


class TestTts:
    def test_first(self):
        html_str = """
        <p>This is a test</p>
        """

        output_html_bytes, frags, last_id = process_xhtml_inplace(html_str.encode(), 0)
        LOG.info(output_html_bytes.decode())

    def test_short_no_punct(self):
        html_str = """
        <body xmlns="http://www.w3.org/1999/xhtml" class="calibre">
<blockquote class="calibre1"><p class="calibre_2"><span class="calibre7">Chapter 3</span></p></blockquote>
<p class="calibre_8">I had my CE Thermodynamics lab right after that, so I didn’t have a chance talk to Hayley. But
    during the lab, a text came in from her.</p>
<p class="calibre_8"><br class="calibre4"/></p>
<p class="calibre_9"><span
        class="italic">You probably shouldn’t say anything here but I figured you’d want to see this</span></p>
<p class="calibre_9"><span class="italic"><br class="calibre4"/></span></p>
<p class="calibre_10"><span class="italic">What?</span></p>
<p class="calibre_10"><span class="italic"><br class="calibre4"/></span></p>
<p class="calibre_9"><span class="italic">Morrigan and I were texting during class.</span></p>
<p class="calibre_8"><span class="italic"><br class="calibre4"/></span></p>
<p class="calibre_8">A screenshot of her message app popped up. It was a conversation between her and Morrigan. Most of
    it was cut off, and she’d just snapped the last exchange.</p>
<p class="calibre_8"><br class="calibre4"/></p>
<p class="calibre_10"><span class="italic">Oh yeah I get it not trying to break you up</span></p>
<p class="calibre_10"><span class="italic"><br class="calibre4"/></span></p>
<p class="calibre_10"><span class="italic">No way</span></p>
<p class="calibre_10"><span class="italic"><br class="calibre4"/></span></p>
<p class="calibre_10"><span class="italic">I wouldn’t do that</span></p>
<p class="calibre_10"><span class="italic"><br class="calibre4"/></span></p>
<p class="calibre_9"><span class="italic">Then what?</span></p>
<p class="calibre_8"><span class="italic"><br class="calibre4"/></span></p>
<p class="calibre_10"><span class="italic">Just saying</span></p>
<p class="calibre_10"><span class="italic"><br class="calibre4"/></span></p>
<p class="calibre_10"><span class="italic">If you guys ever get in the mood for a threesome</span></p>
<p class="calibre_10"><span class="italic"><br class="calibre4"/></span></p>
<p class="calibre_10"><span class="italic">Let me know</span></p>
<p class="calibre_10"><span class="italic"><br class="calibre4"/></span></p>
</body>
        """
        output_html_bytes, frags, last_id = process_xhtml_inplace(html_str.encode(), 0)
        LOG.info(output_html_bytes.decode())
        LOG.info(frags.model_dump_json(indent=2))

    def test_3(self):
        html_str = """
        <body xmlns="http://www.w3.org/1999/xhtml" class="calibre" id="E9OE0-94e3a14dbb3747a29c6a4369d6167083">
<h1 class="block_9" id="id_Toc53256537">CHAPTER 11</h1>
<p class="block_10"> </p>
<p class="block_15">“And so I grant thee my life and soul, oh cruel mistress of battle…”</p>
<p class="block_18"> </p>
<div class="calibre4"><div class="block_13"><span class="bullet_2">- </span><span class="calibre5"><i class="calibre2">The Collected Poetries of Adison Gimble</i></span></div></div>
<p class="block_22">Major General Adison Gimble</p>
<p class="block_10"> </p>
<p class="block_10"> </p>
<p class="block_12">Specifications Request acknowledged.</p>
<p class="block_12">…</p>
<p class="block_12">Combat Assistance Device: Shido. User identification… Accepted.</p>
<p class="block_12">Type: A-TYPE</p>
<p class="block_12">Rank: E3</p>
<p class="block_12">…</p>
<p class="block_12">User Attributes:</p>
<p class="block_12">- Strength: F5</p>
<p class="block_12">- Cognition: F5</p>
<p class="block_12">…</p>
<p class="block_12">CAD Specifications:</p>
<p class="block_12">- Offense: F4</p>
</body>
        """
        output_html_bytes, frags, last_id = process_xhtml_inplace(html_str.encode(), 0)
        LOG.info(output_html_bytes.decode())
        LOG.info(frags.model_dump_json(indent=2))
