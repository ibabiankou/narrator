import decimal

from m3u8.model import StreamInfo, quoted


def str_override(self):
    stream_inf = []
    if self.program_id is not None:
        stream_inf.append("PROGRAM-ID=%d" % self.program_id)
    if self.closed_captions is not None:
        stream_inf.append("CLOSED-CAPTIONS=%s" % self.closed_captions)
    if self.bandwidth is not None:
        stream_inf.append("BANDWIDTH=%d" % self.bandwidth)
    # Change starts here
    if self.subtitles is not None:
        stream_inf.append("SUBTITLES=%s" % quoted(self.subtitles))
    # Change ends here
    if self.average_bandwidth is not None:
        stream_inf.append("AVERAGE-BANDWIDTH=%d" % self.average_bandwidth)
    if self.resolution is not None:
        res = str(self.resolution[0]) + "x" + str(self.resolution[1])
        stream_inf.append("RESOLUTION=" + res)
    if self.frame_rate is not None:
        stream_inf.append(
            "FRAME-RATE=%g"
            % decimal.Decimal(self.frame_rate).quantize(decimal.Decimal("1.000"))
        )
    if self.codecs is not None:
        stream_inf.append("CODECS=" + quoted(self.codecs))
    if self.video_range is not None:
        stream_inf.append("VIDEO-RANGE=%s" % self.video_range)
    if self.hdcp_level is not None:
        stream_inf.append("HDCP-LEVEL=%s" % self.hdcp_level)
    if self.pathway_id is not None:
        stream_inf.append("PATHWAY-ID=" + quoted(self.pathway_id))
    if self.stable_variant_id is not None:
        stream_inf.append("STABLE-VARIANT-ID=" + quoted(self.stable_variant_id))
    if self.req_video_layout is not None:
        stream_inf.append("REQ-VIDEO_LAYOUT=" + quoted(self.req_video_layout))
    return ",".join(stream_inf)

StreamInfo.__str__ = str_override
