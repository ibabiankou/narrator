import { Component, input, OnDestroy, OnInit } from '@angular/core';
import { AudioTrack, Playlist } from '../../core/models/books.dto';
import { MatIcon } from '@angular/material/icon';
import { MatIconButton } from '@angular/material/button';
import { environment } from '../../../environments/environment';
import { BooksService } from '../../core/services/books.service';
import {
  BehaviorSubject,
  combineLatest,
  filter, from,
  interval,
  map, Observable, of,
  Subject,
  Subscription,
  switchMap,
  take,
  takeUntil,
  tap, throwError,
  zip,
} from 'rxjs';
import { AsyncPipe } from '@angular/common';

declare const Amplitude: any;

@Component({
  selector: 'app-player',
  imports: [
    MatIcon,
    MatIconButton,
    AsyncPipe
  ],
  templateUrl: './player.component.html',
  styleUrl: './player.component.scss',
})
export class PlayerComponent implements OnInit, OnDestroy {
  playlist = input.required<Playlist>();

  playerState: PlayerState;

  constructor(private bookService: BooksService) {
    this.playerState = new PlayerState(this.bookService);
  }

  ngOnInit(): void {
    this.playerState.setPlaylist(this.playlist());
  }

  ngOnDestroy(): void {
    this.playerState?.destroy();
  }

  // TODO: Auto-scroll to the currently played item. I should probably simply emmit event what is being played
  //  (upon start and periodically)
  //  and let the page do the scrolling.
}

// A single place for all logic around managing the state of the player.
class PlayerState {
  audioPlayer: AudioPlayer = new AudioPlayer();

  $destroy = new Subject<boolean>();
  // Interval that reads info from Amplitude.
  // readerSubscription: Subscription;
  // Interval that writes progress to the server.
  // writerSubscription: Subscription;

  // tracks: AudioTrack[] = [];
  // // Holds global book time at which each track starts.
  durationSum: number[] = [];

  private readonly $currentTrackIndex = new BehaviorSubject<number>(0);
  private readonly $currentTrackProgressSeconds = new BehaviorSubject<number>(0);

  // Progress from the start of the book.
  private readonly $progressSeconds;
  // Total duration of the narrated part.
  private readonly $totalNarratedSeconds = new BehaviorSubject<number>(0)

  $nowTime;
  $remainingTime;

  $nowPercent;
  $availablePercent = new BehaviorSubject<number>(0);
  $queuedPercent = new BehaviorSubject<number>(0);
  $unavailablePercent = new BehaviorSubject<number>(0);

  constructor(private bookService: BooksService) {
    this.$progressSeconds = zip(this.$currentTrackIndex, this.$currentTrackProgressSeconds)
      .pipe(map(([index, progress]) => this.durationSum[index] + progress));
    this.$nowTime = this.$progressSeconds.pipe(
      map(progressSeconds => secondsToTimeFormat(progressSeconds))
    );
    this.$remainingTime = combineLatest([this.$progressSeconds, this.$totalNarratedSeconds])
      .pipe(map(([nowTime, totalTime]) => secondsToTimeFormat(nowTime - totalTime)));
    this.$nowPercent = combineLatest([this.$progressSeconds, this.$totalNarratedSeconds, this.$availablePercent])
      .pipe(
        map(([nowTime, totalTime, availablePercent]) =>
          totalTime > 0 ? (nowTime / totalTime * availablePercent) : 0
        )
      );

    // Amplitude.init({
    //   songs: this.tracks,
    //   start_song: trackIndex,
    //   playback_speed: 1.15,
    //   debug: !environment.production,
    //   volume: 75,
    //   use_web_audio_api: true,
    //   callbacks: {
    //     song_change: () => this.readProgress()
    //   }
    // });

    // this.readerSubscription = interval(1000)
    //   .pipe(
    //     tap(() => this.$isPlaying.next(Amplitude.getPlayerState() == "playing")),
    //     filter(() => Amplitude.getPlayerState() == "playing"),
    //     takeUntil(this.$destroy),
    //   ).subscribe(() => this.readProgress());
    //
    // this.writerSubscription = interval(5000)
    //   .pipe(
    //     filter(() => Amplitude.getPlayerState() == "playing"),
    //     takeUntil(this.$destroy),
    //   ).subscribe(() => this.updateProgress());
  }

  setPlaylist(playlist: Playlist) {
    this.audioPlayer.setTracks(playlist.tracks);

    this.durationSum = [0];
    for (let i = 0; i < playlist.tracks.length; i++) {
      this.durationSum.push(this.durationSum[i] + playlist.tracks[i].duration);
    }

    let trackIndex = 0;
    if (playlist.progress.section_id) {
      trackIndex = playlist.tracks.findIndex(t => t.section_id == playlist.progress.section_id);
    }
    this.$currentTrackIndex.next(trackIndex);

    this.$currentTrackProgressSeconds.next(playlist.progress.section_progress_seconds || 0)
    this.$totalNarratedSeconds.next(playlist.progress.total_narrated_seconds);

    this.$availablePercent.next(playlist.progress.available_percent);
    this.$queuedPercent.next(playlist.progress.queued_percent);
    this.$unavailablePercent.next(playlist.progress.unavailable_percent);
  }

  private readProgress() {
    const track = Amplitude.getActiveSongMetadata();
    this.$currentTrackIndex.next(track.index);
    this.$currentTrackProgressSeconds.next(Amplitude.getSongPlayedSeconds());
  }

  private updateProgress() {
    combineLatest([this.$currentTrackIndex, this.$currentTrackProgressSeconds])
      .pipe(
        take(1),
        switchMap(([trackIndex, progressSeconds]) => {
          const track = this.audioPlayer.getTrack(trackIndex);
          return this.bookService.updateProgress({
            "book_id": track.book_id,
            "section_id": track.section_id,
            "section_progress_seconds": progressSeconds,
          });
        })
      )
      .subscribe();
  }

  playPause() {
    this.audioPlayer.$isPlaying.pipe(take(1)).subscribe(isPlaying => {
      if (isPlaying) {
        this.audioPlayer.stop();
      } else {
        this.audioPlayer.play();
      }
    })
  }

  destroy() {
    Amplitude.pause();
    this.$destroy.next(true);
    this.$destroy.complete();
  }
}

interface PlayerTrack {
  audioTrack: AudioTrack

  url?: string;
  index: number;

  audioBuffer?: AudioBuffer;
}

class AudioPlayer {
  private audioContext: AudioContext;
  private tracks: PlayerTrack[] = [];
  private $currentTrackSourceNode = new BehaviorSubject<AudioBufferSourceNode | null>(null);

  $currentTrackIndex = new BehaviorSubject<number>(0);
  $currentTrackProgressSeconds = new BehaviorSubject<number>(0);
  $isPlaying = this.$currentTrackSourceNode.pipe(map(node => node != null));

  constructor() {
    this.audioContext = new window.AudioContext();
  }

  setTracks(tracks: AudioTrack[]) {
    this.stop();
    const baseUrl = environment.api_base_url

    this.tracks = tracks.map((track, index) => ({
      audioTrack: track,
      url: `${baseUrl}/books/${track.book_id}/speech/${track.file_name}`,
      index: index
    }));
    this.$currentTrackIndex.next(0);
    this.$currentTrackProgressSeconds.next(0);
  }

  play(index: number | null = null, position_seconds: number = 0) {
    // Start playing track[index], from position_seconds
    // if the index is null, and resume playing the current track or do nothing if it is playing.
    combineLatest([this.$currentTrackIndex, this.$currentTrackProgressSeconds])
      .pipe(take(1))
      .subscribe(([trackIndex, trackProgressSeconds]) => {
        return this.playTrack(this.tracks[trackIndex]);
      });
  }

  stop() {
    this.$currentTrackSourceNode.pipe(take(1)).subscribe(
      (source) => {
        if (source) {
          source.stop();
          this.$currentTrackSourceNode.next(null);
        }
      }
    )
  }

  nextTrack() {
    // Play the next track.
  }

  previousTrack() {
    // Play the previous track.
  }

  private playAudio(audioBuffer: AudioBuffer, offset_seconds: number = 0) {
    // Create an AudioBufferSourceNode
    const source = this.audioContext.createBufferSource();

    // Set the decoded audio data to the source
    source.buffer = audioBuffer;

    // Connect the source node to the destination (the speakers)
    source.connect(this.audioContext.destination);
    source.start(0, offset_seconds); // Start at time 0 seconds
    source.onended = () => {
      source.disconnect(this.audioContext.destination);
    };

    return of(source);
  }

  private playTrack(track: PlayerTrack) {
    console.log(track);
    if (track.url == null) {
      return throwError(() => new Error("Track URL is null"));
    }

    let audioBuffer;
    if (track.audioBuffer != null) {
      audioBuffer = of(track.audioBuffer);
    } else {
      audioBuffer = from(fetch(track.url)).pipe(
        switchMap(response => response.arrayBuffer()),
        switchMap(arrayBuffer => this.audioContext.decodeAudioData(arrayBuffer)),
        tap(audioBuffer => track.audioBuffer = audioBuffer)
      )
    }

    return audioBuffer.pipe(
      switchMap(audioBuffer => this.playAudio(audioBuffer))
    ).subscribe(audioNode => this.$currentTrackSourceNode.next(audioNode));
  }

  getTrack(trackIndex: number) {
    return this.tracks[trackIndex].audioTrack;
  }
}

/**
 * Converts a number of seconds into a time string in (hh:)mm:ss format.
 * If the duration is 1 hour or more, it includes hours (hh:mm:ss).
 * Otherwise, it shows only minutes and seconds (mm:ss).
 *
 * @param totalSeconds The total duration in seconds.
 * @returns The time string in (hh:)mm:ss format.
 */
function secondsToTimeFormat(totalSeconds: number): string {
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
