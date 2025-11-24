import { Component, input, OnInit, signal } from '@angular/core';
import { Section, SpeechStatus } from '../../core/models/books.dto';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import { environment } from '../../../environments/environment';

declare const Amplitude: any;

@Component({
  selector: 'app-player',
  imports: [
    MatIcon,
    MatIconButton
  ],
  templateUrl: './player.component.html',
  styleUrl: './player.component.scss',
})
export class PlayerComponent implements OnInit {
  sections = input.required<Section[]>();

  isPlaying = signal<boolean>(false);
  baseUrl = environment.api_base_url

  ngOnInit(): void {
    const songs = this.sections().filter(section => section.speech_status == SpeechStatus.ready)
      .map(section => {
        return {
          "url": `${this.baseUrl}/books/${section.book_id}/speech/${section.speech_file}`
        }
      });
    console.log(songs);
    Amplitude.init({
      songs: songs
    });
  }
}
