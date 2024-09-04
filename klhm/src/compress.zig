const std = @import("std");
const c = @cImport({
    @cInclude("zstd.h");
});

const data = @import("data.zig");

const Self = @This();

cstream: *c.ZSTD_CStream,
outBuffer: [2048]u8 = undefined, // Buffer to store temporary output of zstd

const CompressionError = error{
    StreamCreationFailed,
    ZSTDError,
};

pub fn init() !Self {
    if (c.ZSTD_createCStream()) |cstream| {
        return Self{ .cstream = cstream };
    }
    return CompressionError.StreamCreationFailed;
}

pub fn deinit(self: *Self) void {
    _ = c.ZSTD_freeCStream(self.cstream);
}

pub fn compressedSizeSlice(self: *Self, slice: []const u8) !usize {
    // Make sure we are in a clean state.
    const r = c.ZSTD_CCtx_reset(self.cstream, c.ZSTD_reset_session_and_parameters);
    if (c.ZSTD_isError(r) != 0) {
        return CompressionError.ZSTDError;
    }
    var inBuffer = c.ZSTD_inBuffer{
        .src = @ptrCast(slice),
        .size = slice.len,
        .pos = 0,
    };
    var outBuffer = c.ZSTD_outBuffer{
        .dst = @ptrCast(&self.outBuffer),
        .size = self.outBuffer.len,
        .pos = 0,
    };
    var len: usize = 0;
    while (true) {
        const result: usize = c.ZSTD_compressStream2(
            self.cstream,
            &outBuffer,
            &inBuffer,
            c.ZSTD_e_end,
        );
        if (c.ZSTD_isError(result) != 0) {
            return CompressionError.ZSTDError;
        }
        len += outBuffer.pos;
        if (result == 0 and (inBuffer.pos == inBuffer.size)) {
            return len;
        }
        outBuffer.pos = 0;
    }
    return len;
}

pub fn compressedSizeIntervalls(self: *Self, slice: []const u8, scopes: *std.ArrayList(data.Scope), checkSat: []const u8) !usize {
    const r = c.ZSTD_CCtx_reset(self.cstream, c.ZSTD_reset_session_and_parameters);
    if (c.ZSTD_isError(r) != 0) {
        return CompressionError.ZSTDError;
    }
    var inBuffer = c.ZSTD_inBuffer{
        .src = @ptrCast(slice),
        .size = 0,
        .pos = 0,
    };
    var outBuffer = c.ZSTD_outBuffer{
        .dst = @ptrCast(&self.outBuffer),
        .size = self.outBuffer.len,
        .pos = 0,
    };
    var len: usize = 0;
    for (scopes.items) |scope| {
        var i: usize = 0;
        while (i < scope.intervals.items.len) : ({
            i += 2;
        }) {
            const start = scope.intervals.items[i];
            const end = scope.intervals.items[i + 1];
            inBuffer.pos = start;
            inBuffer.size = end;
            while (true) {
                const result: usize = c.ZSTD_compressStream2(
                    self.cstream,
                    &outBuffer,
                    &inBuffer,
                    c.ZSTD_e_continue,
                );
                if (c.ZSTD_isError(result) != 0) {
                    return CompressionError.ZSTDError;
                }
                len += outBuffer.pos;
                if (result == 0 and (inBuffer.pos == inBuffer.size)) {
                    outBuffer.pos = 0;
                    break;
                }
                outBuffer.pos = 0;
            }
        }
    }
    if (inBuffer.pos != inBuffer.size or outBuffer.pos != 0) {
        return CompressionError.ZSTDError;
    }
    // Flush anything remaining
    while (true) {
        inBuffer.src = @ptrCast(checkSat);
        inBuffer.pos = 0;
        inBuffer.size = checkSat.len;
        const result: usize = c.ZSTD_compressStream2(
            self.cstream,
            &outBuffer,
            &inBuffer,
            c.ZSTD_e_end,
        );
        if (c.ZSTD_isError(result) != 0)
            return CompressionError.ZSTDError;
        len += outBuffer.pos;
        if (result == 0 and (inBuffer.pos == inBuffer.size))
            break;
        outBuffer.pos = 0;
    }
    return len;
}

test "get zstd version" {
    const version = c.ZSTD_versionNumber();
    try std.testing.expect(version > 0);
}

test "create a compression context" {
    const cstream = c.ZSTD_createCStream();
    try std.testing.expect(c.ZSTD_sizeof_CCtx(cstream) > 0);

    const result = c.ZSTD_freeCStream(cstream);
    try std.testing.expectEqual(result, 0);
}

test "compress a fixed buffer" {
    const cstream = c.ZSTD_createCStream();
    defer _ = c.ZSTD_freeCStream(cstream);

    const input = "compress this text please please please please!";

    var inBuffer = c.ZSTD_inBuffer{
        .src = @ptrCast(input),
        .size = input.len,
        .pos = 0,
    };
    var outputStorage: [512]u8 = undefined;

    var outBuffer = c.ZSTD_outBuffer{
        .dst = @ptrCast(&outputStorage),
        .size = outputStorage.len,
        .pos = 0,
    };

    const result: usize = c.ZSTD_compressStream2(
        cstream,
        &outBuffer,
        &inBuffer,
        c.ZSTD_e_end,
    );
    // Should be done in one call
    try std.testing.expectEqual(result, 0);
    try std.testing.expect(outBuffer.pos > 0);
}
