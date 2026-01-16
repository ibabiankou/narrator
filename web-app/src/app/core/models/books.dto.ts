import { SafeResourceUrl } from '@angular/platform-browser';

export interface CreateBookRequest {
  id: string;
  title: string;
  pdf_temp_file_id: string;
}

export enum BookStatus {
  processing = "processing",
  ready = "ready"
}

export interface BookDetails {
  id: string;
  title: string;
  pdf_file_name: string;
  number_of_pages: number;
  status: string;
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

  file_url: SafeResourceUrl;

  // Sections of the book starting on this page.
  sections: Section[];
}

export interface BookContent {
  pages: BookPage[];
}

export interface AudioTrack {
  book_id: string;
  section_id: number;
  status: string;
  file_name: string;
  duration: number;
}

export interface PlaybackProgress {
  global_progress_seconds: number;
  total_narrated_seconds: number;

  available_percent: number;
  queued_percent: number;
  unavailable_percent: number;

  sync_current_section: boolean;
  playback_rate: number;
}

export interface Playlist {
  progress: PlaybackProgress;
  tracks: AudioTrack[];
}

export interface PlaybackStateUpdate {
  book_id: string;
  data: { [key: string]: any };
}
