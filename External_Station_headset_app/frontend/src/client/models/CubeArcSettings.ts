/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type CubeArcSettings = {
    difficulty?: number;
    iterations?: number;
    game_type?: string;
    start_side?: CubeArcSettings.start_side;
};
export namespace CubeArcSettings {
    export enum start_side {
        LEFT = 'left',
        RIGHT = 'right',
    }
}

