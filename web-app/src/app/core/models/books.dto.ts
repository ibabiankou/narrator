export interface CreateBookRequest {
  id: string;
  title: string;
  pdf_temp_file_id: string;
}

export enum BookStatus {
  processing = "processing",
  ready_for_metadata_review = "ready_for_metadata_review",
  ready = "ready"
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
  pdf_file_name: string;
  number_of_pages: number;
  status: string;
}

export interface BookStats {
  total_narrated_seconds: number;
  available_percent: number;
  total_size_bytes: number;
}

export interface Section {
  id: number;
  book_id: string;
  // Index of the section within the book.
  section_index: number;
  // Index of the page where the section starts.
  page_index: number;

  content: string;
}

export interface BookPage {
  // Index of the page within the book.
  index: number;
  // File name of the page. It can be used to download the page.
  file_name: string;

  file_url: string;

  // Sections of the book starting on this page.
  sections: Section[];
}

export interface BookWithContent {
  overview: BookOverview;
  stats: BookStats;
  pages: BookPage[];
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
