const std = @import("std");
const zstd = @cImport({
    @cInclude("zstd.h");
});

test "get zstd version" {
    const version = zstd.ZSTD_versionNumber();
    try std.testing.expect(version > 0);
}

test "create a compression context" {
    var cstream = zstd.ZSTD_createCStream();
    try std.testing.expect(zstd.ZSTD_sizeof_CCtx(cstream) > 0);

    const result = zstd.ZSTD_freeCStream(cstream);
    try std.testing.expectEqual(result, 0);
}

test "compress a fixed buffer" {
    var cstream = zstd.ZSTD_createCStream();
    defer _ = zstd.ZSTD_freeCStream(cstream);

    const input = "compress this text please please please please!";

    var inBuffer = zstd.ZSTD_inBuffer{
        .src = @ptrCast(input),
        .size = input.len,
        .pos = 0,
    };
    var outputStorage: [512]u8 = undefined;

    var outBuffer = zstd.ZSTD_outBuffer{
        .dst = @ptrCast(&outputStorage),
        .size = outputStorage.len,
        .pos = 0,
    };

    const result: usize = zstd.ZSTD_compressStream2(
        cstream,
        &outBuffer,
        &inBuffer,
        zstd.ZSTD_e_end,
    );
    // Should be done in one call
    try std.testing.expectEqual(result, 0);
    try std.testing.expect(outBuffer.pos > 0);
}
