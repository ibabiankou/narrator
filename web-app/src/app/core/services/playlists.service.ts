import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { PlaybackStateUpdate, Playlist } from '../models/books.dto';

@Injectable({
  providedIn: 'root'
})
export class PlaylistsService {

  private apiUrl = `${environment.api_base_url}/playlists`;

  constructor(private http: HttpClient) {
  }

  getPlaylist(bookId: string) {
    return this.http.get<Playlist>(`${this.apiUrl}/${bookId}`);
  }

  updateProgress(progress: PlaybackStateUpdate) {
    return this.http.post<void>(`${this.apiUrl}/${progress.book_id}/progress`, progress);
  }
}
