import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { PlaybackProgressUpdate, Playlist } from '../models/books.dto';

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

  updateProgress(progress: PlaybackProgressUpdate) {
    return this.http.post<void>(`${this.apiUrl}/${progress.book_id}/progress`, progress);
  }

  generateTracks(bookId: string, sectionIds: number[] = [], limit: number = 5) {
    let params = new HttpParams({
      fromObject: {
        limit: limit
      }
    });
    return this.http.post<Playlist>(`${this.apiUrl}/${bookId}/generate`, sectionIds, {params: params});
  }

  getTracks(bookId: string, sectionIds: number[]) {
    let params = new HttpParams({
      fromObject: {
        sections: sectionIds
      }
    });
    return this.http.get<Playlist>(`${this.apiUrl}/${bookId}/tracks`, {params: params});
  }
}
