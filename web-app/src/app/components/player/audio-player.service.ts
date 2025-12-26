import { AudioTrack } from '../../core/models/books.dto';
import { environment } from '../../../environments/environment';
import {
  BehaviorSubject,
  combineLatest, combineLatestWith, distinct,
  filter,
  interval,
  map,
  Subject,
  Subscription, switchMap,
  take,
  takeUntil,
  zip,
} from 'rxjs';
import { Injectable } from '@angular/core';
import { PlaylistsService } from '../../core/services/playlists.service';

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

  private tracks: PlayerTrack[] = [];
  // Holds global book time at which each track starts.
  private durationSum: number[] = [0];

  private $destroy = new Subject<boolean>();

  private readerSubscription: Subscription;
  private writerSubscription: Subscription;

  $trackIndex = new BehaviorSubject<number>(0);
  private $trackOffset = new BehaviorSubject<number>(0);
  private $currentContextTime = new BehaviorSubject<number>(0);

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

  $playbackRate = new BehaviorSubject<number>(1);

  constructor(private playlistService: PlaylistsService) {
    this.$playbackRate.subscribe(() => {
      if (this.audio) {
        this.audio.playbackRate = this.$playbackRate.value;
      }
    });
    zip([this.$trackIndex, this.$trackOffset])
      .pipe(
        takeUntil(this.$destroy),
        filter(([trackIndex, _]) => trackIndex >= 0 && trackIndex < this.tracks.length),
        filter(() => this.$status.value == PlayerStatus.playing)
      ).subscribe(([trackIndex, trackOffset]) => {
        this.audio?.pause();

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

        audio.addEventListener('error', (err) => {
          console.log('Unable to load audio.', err);
        });

        audio.currentTime = trackOffset;
        audio.preservesPitch = true;
        audio.playbackRate = this.$playbackRate.value;

        audio.play();
      }
    );

    this.readerSubscription = interval(1000)
      .pipe(
        combineLatestWith(this.$isPlaying),
        filter(([_, isPlaying]) => isPlaying),
        takeUntil(this.$destroy),
      ).subscribe(() => this.readProgress());

    this.writerSubscription = interval(5000)
      .pipe(
        combineLatestWith(this.$isPlaying),
        filter(([_, isPlaying]) => isPlaying),
        takeUntil(this.$destroy),
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

  destroy() {
    this.$destroy.next(true);
    this.readerSubscription.unsubscribe();
    this.writerSubscription.unsubscribe();
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

  adjustPlaybackRate(adjustment: number) {
    const maxValue = 2;
    const minValue = 0.5;
    const newRate = this.$playbackRate.value + adjustment;
    this.$playbackRate.next(Math.max(Math.min(newRate, maxValue), minValue));
  }

  setPlaybackRate(playback_rate: number) {
    this.$playbackRate.next(playback_rate);
  }
}
