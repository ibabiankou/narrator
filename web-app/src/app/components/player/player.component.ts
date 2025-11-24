import { Component, computed, effect, input, OnInit, signal } from '@angular/core';
import { Section, SpeechStatus } from '../../core/models/books.dto';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import { environment } from '../../../environments/environment';
import { interval, take } from 'rxjs';

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

  readyWidth = computed(() => {
    const total = this.sections().length
    const ready = this.sections().filter(section => section.speech_status == SpeechStatus.ready).length
    return ready / total * 100;
  });
  missingWidth = computed(() => {
    const total = this.sections().length
    const missing = this.sections().filter(section => section.speech_status == SpeechStatus.missing).length;
    return missing / total * 100;
  });

  constructor() {
    effect(() => {
      let sectionsInPlaylist = new Set<number>();
      Amplitude.getSongs().forEach((song: { section_id: number; }) => sectionsInPlaylist.add(song.section_id));

      this.sections()
        .filter(section => section.speech_status == SpeechStatus.ready)
        .filter(section => !sectionsInPlaylist.has(section.id))
        .forEach(section => Amplitude.addSong(
          {
            "section_id": section.id,
            "url": `${this.baseUrl}/books/${section.book_id}/speech/${section.speech_file}`
          }
        ))
    });
  }

  ngOnInit(): void {
    const songs = this.sections().filter(section => section.speech_status == SpeechStatus.ready)
      .map(section => {
        return {
          "section_id": section.id,
          "url": `${this.baseUrl}/books/${section.book_id}/speech/${section.speech_file}`
        }
      });

    Amplitude.init({
      songs: songs,
      playback_speed: 1.1
    });

    interval(1000).pipe(take(25))
      .subscribe(x => console.log("Songs in playlist: ", Amplitude.getSongs().length));
  }

  // TODO: Implement progress bar. Available, queued, unavailable.

  // TODO: Render current position in time and total playback time.
  //  How and when calculate this?

  // TODO: Append songs as more content is loaded. < Use state for this?

  // TODO: Auto-scroll to the currently played item. I should probably simply emmit event what is being played
  //  (upon start and periodically)
  //  and let the page do the scrolling.

  playPause() {
    if (this.isPlaying()) {
      Amplitude.pause();
    } else {
      Amplitude.play();
    }
    this.isPlaying.update(value => !value);
  }
}
