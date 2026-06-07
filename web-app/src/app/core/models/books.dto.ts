export enum BookStatus {
  /** Just uploaded book is going through initial processing. */
  processing = "processing",

  /** Book is stored, user can proceed to select the content to be narrated. */
  ready_for_toc_review = "ready_for_toc_review",

  /** The book is ready to be narrated, but waiting in the queue. */
  queued = "queued",

  /** The book is being narrated. */
  narrating = "narrating",

  /** The book is fully narrated and ready for playback or download. */
  ready = "ready"
}

const BookStatusRank: Record<BookStatus, number> = {
  [BookStatus.processing]: 1,
  [BookStatus.ready_for_toc_review]: 4,
  [BookStatus.queued]: 5,
  [BookStatus.narrating]: 6,
  [BookStatus.ready]: 7,
};

export namespace BookStatus {
  /**
   *  Returns true if the left status is greater than or equal to the right status.
   */
  export function ge(left: BookStatus, right: BookStatus): boolean {
    return BookStatusRank[left] >= BookStatusRank[right];
  }
}

export interface BookMetadata {
  cover?: string;
  title?: string;
  series?: string;
  description?: string;

  authors: string[];
  isbns: string[];
}

export interface BookOverview extends BookMetadata {
  id: string;
  owner_id: string;
  status: BookStatus;
}

export interface BookDetails extends BookOverview {
  book_file_key: string;
}

export interface MetadataCandidate extends BookMetadata {
  source: string;
}

export interface MetadataCandidates {
  candidates: MetadataCandidate[];
  preferred_index: number;
  selected_index?: number;
}

export interface BookMetadataForReview {
  overview: BookOverview;
  metadata_candidates: MetadataCandidates;
}

export interface PlaybackInfo {
  book_id: string;
  data: { [key: string]: any };
}

/**
 * Metadata of a locally downloaded book.
 */
export interface DownloadInfo {
  id: string;

  fragments_total: number;
  fragments_downloaded: number;
}

export interface Settings {
  [key: string]: any
}

export interface TocItem {
  href: string;
  title?: string;
  narrate: boolean;
}
