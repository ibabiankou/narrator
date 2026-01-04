import { AudioTrack, BookDetails } from '../../core/models/books.dto';
import { environment } from '../../../environments/environment';
import {
  BehaviorSubject,
  combineLatest, combineLatestWith, distinct,
  filter,
  interval,
  map, Observable,
  switchMap,
  take,
  zip,
} from 'rxjs';
import { Injectable } from '@angular/core';
import { PlaylistsService } from '../../core/services/playlists.service';
import { PlaybackPosition } from '../../core/models/player.dto';

interface PlayerTrack {
  audioTrack: AudioTrack

  url: string;
  index: number;
}

enum PlayerStatus {
  stopped = "stopped",
  playing = "playing",
  paused = "paused",
}

/**
 * Responsible for playback logic: Playing each track, navigating back and forth, changing tracks.
 */
@Injectable({providedIn: 'root'})
export class AudioPlayerService {
  private $status = new BehaviorSubject<PlayerStatus>(PlayerStatus.stopped);
  private audio: HTMLAudioElement | null = null;

  $bookDetails = new BehaviorSubject<BookDetails | null>(null);
  private tracks: PlayerTrack[] = [];
  // Holds global book time at which each track starts.
  private durationSum: number[] = [0];

  $trackIndex = new BehaviorSubject<number>(0);
  private $trackOffset = new BehaviorSubject<number>(0);
  private $currentContextTime = new BehaviorSubject<number>(0);
  $playbackRate = new BehaviorSubject<number>(1);

  $isPlaying = this.$status.pipe(map((status) => status == PlayerStatus.playing));

  $audioTrack = combineLatest([this.$trackIndex, this.$isPlaying])
    .pipe(
      filter(([_, isPlaying]) => isPlaying),
      map(([trackIndex, _]) => this.tracks[trackIndex]?.audioTrack),
      filter(track => track != null),
      distinct()
    );

  $trackProgress = combineLatest([this.$trackIndex, this.$currentContextTime])
    .pipe(
      map(([trackIndex, progress]) => ({
        track: this.tracks[trackIndex]?.audioTrack,
        progressSeconds: progress,
      }))
    );

  // Progress from the start of the book.
  $globalProgressSeconds = combineLatest([this.$trackIndex, this.$currentContextTime])
    .pipe(map(([index, progress]) => this.durationSum[index] + progress));

  $playbackPosition: Observable<PlaybackPosition> = combineLatest([this.$playbackRate, this.$globalProgressSeconds])
    .pipe(filter(() => this.tracks.length > 0))
    .pipe(map(([playbackRate, globalProgressSeconds]) => {
      const lastTrackIndex = this.tracks.length-1;
      const lastTrackDuration = this.tracks[lastTrackIndex].audioTrack.duration;
      const lastTrackStartAt = this.durationSum[lastTrackIndex];
      const duration = lastTrackStartAt + lastTrackDuration;

      return {
        "duration": duration,
        "playbackRate": playbackRate,
        "position": globalProgressSeconds
      };
    }));

  constructor(private playlistService: PlaylistsService) {
    this.$playbackRate.subscribe(() => {
      if (this.audio) {
        this.audio.playbackRate = this.$playbackRate.value;
      }
    });
    zip([this.$trackIndex, this.$trackOffset])
      .pipe(
        filter(([trackIndex, _]) => trackIndex >= 0 && trackIndex < this.tracks.length),
        filter(() => this.$status.value == PlayerStatus.playing)
      ).subscribe(([trackIndex, trackOffset]) => {
        this.stopTheMusic();

        const track = this.tracks[trackIndex];
        if (track == null) {
          console.log("Invalid track index");
          return;
        }

        const audio = new Audio(track.url);
        this.audio = audio;

        audio.addEventListener('timeupdate', () => this.readProgress());
        audio.addEventListener('ended', () => {
          if (this.tracks.length > trackIndex + 1) {
            this.playTrack(trackIndex + 1, 0);
          }
        });

        audio.currentTime = trackOffset;
        audio.preservesPitch = true;
        audio.playbackRate = this.$playbackRate.value;

        audio.play();
      }
    );

    interval(1000)
      .pipe(
        combineLatestWith(this.$isPlaying),
        filter(([_, isPlaying]) => isPlaying),
      ).subscribe(() => this.readProgress());

    interval(5000)
      .pipe(
        combineLatestWith(this.$isPlaying),
        filter(([_, isPlaying]) => isPlaying),
      ).subscribe(() => this.updateProgress());
  }

  private readProgress() {
    if (this.audio) {
      this.$currentContextTime.next(this.audio.currentTime);
    }
  }

  private updateProgress() {
    combineLatest([this.$trackProgress, this.$playbackRate])
      .pipe(
        take(1),
        switchMap(([{track, progressSeconds}, playbackRate]) => {
          return this.playlistService.updateProgress({
            "book_id": track.book_id,
            "section_id": track.section_id,
            "section_progress_seconds": progressSeconds,
            // TODO: Replace POST with PATCH, so that all fields in request are optional.
            //  And API updates only provided fields.
            // "sync_current_section": this.syncCurrentSection(),
            "sync_current_section": true,
            "playback_rate": playbackRate
          });
        })
      ).subscribe();
  }

  getNumberOfTracks() {
    return this.tracks.length;
  }

  addTracks(tracks: AudioTrack[]) {
    const baseUrl = environment.api_base_url

    const length = tracks.length;
    let newTracks: PlayerTrack[] = tracks.map((track, index) => ({
      audioTrack: track,
      url: `${baseUrl}/books/${track.book_id}/speech/${track.file_name}`,
      index: length + index
    }));

    for (let i = 0; i < tracks.length; i++) {
      this.durationSum.push(this.durationSum[this.durationSum.length - 1] + tracks[i].duration);
    }

    this.tracks.push(...newTracks);
  }

  playTrack(trackIndex: number, offsetSeconds: number) {
    this.$trackIndex.next(trackIndex);
    this.$trackOffset.next(offsetSeconds);
    this.$currentContextTime.next(offsetSeconds);
  }

  play() {
    combineLatest([this.$status, this.$trackIndex, this.$trackOffset]).pipe(take(1)).subscribe(
      ([status, index, offset]) => {
        this.$status.next(PlayerStatus.playing);
        if (status == PlayerStatus.paused) {
          this.audio?.play();
        } else if (status == PlayerStatus.stopped) {
          this.playTrack(index, offset);
        }
      });
  }

  pause() {
    if (this.audio) {
      this.audio.pause();
      this.readProgress();
      this.$status.next(PlayerStatus.paused);
    }
  }

  next() {
    this.$trackIndex.pipe(take(1)).subscribe(
      (current) => {
        const next = current + 1;
        if (next >= this.tracks.length) {
          return;
        }
        this.playTrack(next, 0);
      });
  }

  previous() {
    this.$trackIndex.pipe(take(1)).subscribe(
      (current) => {
        const prev = current - 1;
        if (prev < 0) {
          return;
        }
        this.playTrack(prev, 0);
      });
  }

  getTrack(trackIndex: number) {
    return this.tracks[trackIndex].audioTrack;
  }

  reset() {
    this.$status.next(PlayerStatus.stopped);
    this.$trackIndex.next(0);
    this.$trackOffset.next(0);
    this.$currentContextTime.next(0);
    this.$playbackRate.next(1);

    this.stopTheMusic();
    this.tracks = [];
    this.durationSum = [0]
    this.$bookDetails.next(null);
  }

  seek(adjustment: number) {
    this.readProgress();
    combineLatest([this.$trackIndex, this.$currentContextTime]).pipe(take(1)).subscribe(
      ([trackIndex, trackProgressSeconds]) => {
        let track = this.getTrack(trackIndex);
        let newProgress = trackProgressSeconds + adjustment;

        if (newProgress < 0) {
          if (trackIndex == 0) {
            // Start from the beginning if it's the first track.
            this.playTrack(0, 0);
            return;
          } else {
            // It's not the first track, so go to the previous track.
            track = this.getTrack(trackIndex - 1);
            newProgress += track.duration;
            this.playTrack(trackIndex - 1, newProgress);
            return;
          }
        } else if (newProgress > track.duration) {
          if (trackIndex == this.tracks.length - 1) {
            // It's the last track, so seek the end. It should stop playback.
            this.playTrack(trackIndex, track.duration);
            return;
          } else {
            // Go to the next track.
            newProgress -= track.duration;
            this.playTrack(trackIndex + 1, newProgress);
            return;
          }
        } else {
          // We are within the current track, so simply change the progress.
          this.playTrack(trackIndex, newProgress);
          return;
        }
      });
  }

  seekTo(seekTime: number | undefined) {
    if (seekTime == undefined) {
      return;
    }

    for (let i = 0; i < this.durationSum.length; i++) {
      if (this.durationSum[i] > seekTime) {
        const trackIndex = i - 1;
        const trackOffset = seekTime - this.durationSum[trackIndex];
        this.playTrack(trackIndex, trackOffset);
        return;
      }
    }
  }

  adjustPlaybackRate(adjustment: number) {
    const maxValue = 2;
    const minValue = 0.5;
    const newRate = this.$playbackRate.value + adjustment;
    this.$playbackRate.next(Math.max(Math.min(newRate, maxValue), minValue));
  }

  setPlaybackRate(playback_rate: number) {
    this.$playbackRate.next(playback_rate);
  }

  private stopTheMusic() {
    if (!this.audio) {
      return;
    }

    this.audio.pause();
    this.audio.src = '';
    this.audio.load();

    this.audio = null;
  }

  setBookDetails(book: BookDetails) {
    this.$bookDetails.next(book);
  }
}
