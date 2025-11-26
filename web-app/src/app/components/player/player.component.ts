import { Component, input, OnInit, signal } from '@angular/core';
import { Playlist } from '../../core/models/books.dto';
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
  playlist = input.required<Playlist>();

  isPlaying = signal<boolean>(false);
  baseUrl = environment.api_base_url

  constructor() {
  }

  ngOnInit(): void {
    const tracks = this.playlist().tracks;
    const sectionId = this.playlist().progress.section_id;
    let activeIndex = 0;
    let activeProgress = 0;
    if (sectionId != null) {
      // We are resuming, so let's find what to play
      for (let i = 0; i < tracks.length; i++) {
        if (tracks[i].section_id == sectionId) {
          activeIndex = i;
          activeProgress = this.playlist().progress.section_progress_seconds / tracks[i].duration * 100;
          break;
        }
      }
    }

    for (let i = 0; i < tracks.length; i++) {
      let track = tracks[i];
      track.url = `${this.baseUrl}/books/${track.book_id}/speech/${track.file_name}`
    }

    Amplitude.init({
      songs: tracks,
      start_song: activeIndex,
      playback_speed: 1.1,
      debug: !environment.production
    });
    Amplitude.setSongPlayedPercentage(activeProgress);
  }

  nowPercent() {
    const progress = this.playlist().progress
    return progress.available_percent * progress.global_progress_seconds / progress.total_narrated_seconds;
  }

  /**
   * Converts a number of seconds into a time string in (hh:)mm:ss format.
   * If the duration is 1 hour or more, it includes hours (hh:mm:ss).
   * Otherwise, it shows only minutes and seconds (mm:ss).
   *
   * @param totalSeconds The total duration in seconds.
   * @returns The time string in (hh:)mm:ss format.
   */
  secondsToTimeFormat(totalSeconds: number): string {
    const sign = totalSeconds >= 0 ? '' : '-';
    const absSeconds = Math.abs(totalSeconds);

    // 1. Calculate the components
    const seconds = Math.floor(absSeconds % 60);
    const minutes = Math.floor((absSeconds / 60) % 60);
    const hours = Math.floor(absSeconds / 3600);

    // 2. Pad the minutes and seconds with a leading zero if they are less than 10
    const ss = seconds.toString().padStart(2, '0');
    const mm = minutes.toString().padStart(2, '0');

    // 3. Conditional formatting for hours
    if (hours > 0) {
      // Pad hours and include them in the format: hh:mm:ss
      const hh = hours.toString();
      return `${sign}${hh}:${mm}:${ss}`;
    } else {
      // Format as mm:ss
      return `${sign}${mm}:${ss}`;
    }
  }

  nowTime() {
    const progress = this.playlist().progress
    return this.secondsToTimeFormat(progress.global_progress_seconds);
  }

  remainingTime() {
    const progress = this.playlist().progress
    return this.secondsToTimeFormat(progress.global_progress_seconds - progress.total_narrated_seconds);
  }


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
