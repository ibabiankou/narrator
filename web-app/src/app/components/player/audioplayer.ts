import { AudioTrack } from '../../core/models/books.dto';
import { environment } from '../../../environments/environment';
import {
  BehaviorSubject,
  combineLatest, combineLatestWith, distinct,
  filter, from,
  interval,
  map, of,
  Subject,
  Subscription,
  switchMap,
  take,
  takeUntil,
  tap, throwError, zip,
} from 'rxjs';

interface PlayerTrack {
  audioTrack: AudioTrack

  url?: string;
  index: number;

  arrayBuffer?: ArrayBuffer;
  // Caching decoded audio might end up taking a lot of memory.
  audioBuffer?: AudioBuffer;
}

enum PlayerStatus {
  stopped = "stopped",
  playing = "playing",
  paused = "paused",
}

/**
 * Responsible for playback logic: Playing each track, navigating back and forth, changing tracks.
 */
export class AudioPlayer {
  private $status = new BehaviorSubject<PlayerStatus>(PlayerStatus.stopped);
  private $audioContext = new BehaviorSubject<AudioContext | null>(null);

  private tracks: PlayerTrack[] = [];
  // Holds global book time at which each track starts.
  private durationSum: number[] = [0];

  private $destroy = new Subject<boolean>();

  readerSubscription: Subscription;

  $trackIndex = new BehaviorSubject<number>(0);
  private $trackOffset = new BehaviorSubject<number>(0);
  private $currentContextTime = new BehaviorSubject<number>(0);
  private $currentTrackProgressSeconds = combineLatest([this.$trackOffset, this.$currentContextTime])
    .pipe(map(([offset, currentTime]) => offset + currentTime));

  $isPlaying = this.$status.pipe(map((status) => status == PlayerStatus.playing));

  $audioTrack = combineLatest([this.$trackIndex, this.$isPlaying])
    .pipe(
      filter(([_, isPlaying]) => isPlaying),
      map(([trackIndex, _]) => this.tracks[trackIndex]?.audioTrack),
      filter(track => track != null),
      distinct()
    );

  $trackProgress = combineLatest([this.$trackIndex, this.$currentTrackProgressSeconds])
    .pipe(
      map(([trackIndex, progress]) => ({
        track: this.tracks[trackIndex]?.audioTrack,
        progressSeconds: progress,
      }))
    );

  // Progress from the start of the book.
  $globalProgressSeconds = combineLatest([this.$trackIndex, this.$currentTrackProgressSeconds])
    .pipe(map(([index, progress]) => this.durationSum[index] + progress));

  constructor() {
    zip([this.$trackIndex, this.$trackOffset])
      .pipe(
        takeUntil(this.$destroy),
        filter(([trackIndex, _]) => trackIndex >= 0 && trackIndex < this.tracks.length),
        switchMap(
          ([trackIndex, trackOffset]) => {
            return this.$status.pipe(
              take(1),
              filter(status => status == PlayerStatus.playing),
              switchMap(() => {
                this.$audioContext.pipe(take(1)).subscribe(ac => ac?.close());

                const track = this.tracks[trackIndex];
                if (track == null) {
                  return throwError(() => new Error("Invalid track index"));
                }

                let audioContext = new AudioContext();
                this.$audioContext.next(audioContext);

                let audioBuffer;
                if (track.audioBuffer != null) {
                  audioBuffer = of(track.audioBuffer);
                } else if (track.url) {
                  audioBuffer = from(fetch(track.url)).pipe(
                    switchMap(response => response.arrayBuffer()),
                    switchMap(arrayBuffer => audioContext.decodeAudioData(arrayBuffer)),
                    tap(audioBuffer => track.audioBuffer = audioBuffer)
                  )
                } else {
                  return throwError(() => new Error("Track without URL"));
                }

                return audioBuffer.pipe(
                  switchMap(audioBuffer => this.connectSource(audioContext, audioBuffer)),
                  tap(source => {
                    source.start(0, trackOffset);
                    source.addEventListener("ended", () => {
                      this.readProgress();
                      if (this.tracks.length > trackIndex + 1) {
                        this.$trackIndex.next(trackIndex + 1);
                        this.$trackOffset.next(0);
                      }
                    });
                  })
                );
              }));
          }
        )
      ).subscribe();

    this.readerSubscription = interval(1000)
      .pipe(
        combineLatestWith(this.$isPlaying),
        filter(([_, isPlaying]) => isPlaying),
        takeUntil(this.$destroy),
      ).subscribe(() => this.readProgress());
  }

  private readProgress() {
    this.$audioContext
      .pipe(filter(ac => ac != null), take(1))
      .subscribe((audioContext) => {
        this.$currentContextTime.next(audioContext.currentTime);
      });
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

  setProgress(startTrackIndex: number, trackOffsetSeconds: number) {
    this.$trackIndex.next(startTrackIndex);
    this.$trackOffset.next(trackOffsetSeconds);
  }

  play() {
    combineLatest([this.$status, this.$audioContext, this.$trackIndex, this.$trackOffset]).pipe(take(1)).subscribe(
      ([status, audioContext, index, offset]) => {
        this.$status.next(PlayerStatus.playing);
        if (status == PlayerStatus.paused) {
          audioContext?.resume();
        } else if (status == PlayerStatus.stopped) {
          this.$trackIndex.next(index);
          this.$trackOffset.next(offset);
        }
      });
  }

  pause() {
    this.$audioContext.pipe(filter(ac => ac != null), take(1))
      .subscribe(
        (audioContext) => {
          audioContext.suspend();
          this.readProgress();
          this.$status.next(PlayerStatus.paused);
        }
      )
  }

  next() {
    this.$trackIndex.pipe(take(1)).subscribe(
      (current) => {
        const next = current + 1;
        if (next >= this.tracks.length) {
          return;
        }
        this.$trackIndex.next(next);
        this.$trackOffset.next(0);
      });
  }

  previous() {
    this.$trackIndex.pipe(take(1)).subscribe(
      (current) => {
        const prev = current - 1;
        if (prev < 0) {
          return;
        }
        this.$trackIndex.next(prev);
        this.$trackOffset.next(0);
      });
  }

  private connectSource(audioContext: AudioContext, audioBuffer: AudioBuffer) {
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    return of(source);
  }

  getTrack(trackIndex: number) {
    return this.tracks[trackIndex].audioTrack;
  }

  destroy() {
    this.$destroy.next(true);
  }

  seek(adjustment: number) {
    this.readProgress();
    combineLatest([this.$trackIndex, this.$currentTrackProgressSeconds]).pipe(take(1)).subscribe(
      ([trackIndex, trackProgressSeconds]) => {
        let track = this.getTrack(trackIndex);
        let newProgress = trackProgressSeconds + adjustment;

        if (newProgress < 0) {
          if (trackIndex == 0) {
            // Start from the beginning if it's the first track.
            this.$trackIndex.next(0);
            this.$trackOffset.next(0);
            return;
          } else {
            // It's not the first track, so go to the previous track.
            track = this.getTrack(trackIndex - 1);
            newProgress += track.duration;
            this.$trackIndex.next(trackIndex - 1);
            this.$trackOffset.next(newProgress);
            return;
          }
        } else if (newProgress > track.duration) {
          if (trackIndex == this.tracks.length - 1) {
            // It's the last track, so seek the end. It should stop playback.
            this.$trackIndex.next(trackIndex);
            this.$trackOffset.next(track.duration);
            return;
          } else {
            // Go to the next track.
            newProgress -= track.duration;
            this.$trackIndex.next(trackIndex + 1);
            this.$trackOffset.next(newProgress);
            return;
          }
        } else {
          // We are within the current track, so simply change the progress.
          this.$trackIndex.next(trackIndex);
          this.$trackOffset.next(newProgress);
          return;
        }
      });
  }
}
