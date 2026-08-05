export interface MotionTarget {}
export interface Point { x: number; y: number }

export interface PropertyMotion {
  withDuration(seconds: number): PropertyMotion;
}

export declare class CanonicalMotion {
  static to(
    target: MotionTarget,
    property: string,
    destination: unknown,
  ): PropertyMotion;
}

