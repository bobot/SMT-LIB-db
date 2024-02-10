const std = @import("std");
const fs = std.fs;
const print = std.debug.print;

const BenchmarkData = struct {
    logic: ?[]const u8 = null,
    size: usize = 0,
    compressedSize: usize = 0,
    license: ?[]const u8 = null,
    generatedOn: ?[]const u8 = null,
    generatedBy: ?[]const u8 = null,
    generator: ?[]const u8 = null,
    application: ?[]const u8 = null,
    description: ?[]const u8 = null,
    category: ?[]const u8 = null,
    subbenchmarkCount: usize = 0,
    isIncremental: bool = false,
};

const SubBenchmarkData = struct {
    normalizedSize: ?usize = null,
    compressedSize: ?usize = null,
    assertsCount: ?usize = null,
    declareFunCount: ?usize = null,
    declareSortCount: ?usize = null,
    defineFunCount: ?usize = null,
    defineSortCount: ?usize = null,
    maxTermDepth: ?usize = null,
};

const Scope = struct {
    intervals: std.ArrayList(usize),
};

const Commands = enum {
    assert,
    check_sat,
    check_sat_assuming,
    declare_const,
    declare_datatype,
    declare_datatypes,
    declare_fun,
    declare_sort,
    define_fun,
    define_fun_rec,
    define_funs_rec,
    define_sort,
    echo,
    exit,
    get_assertions,
    get_assignment,
    get_info,
    get_model,
    get_option,
    get_proof,
    get_unsat_assumptions,
    get_unsat_core,
    get_value,
    pop,
    push,
    reset,
    reset_assertions,
    set_info,
    set_logic,
    set_option,
};

const CmdMap = std.ComptimeStringMap(Commands, .{
    .{ "assert", .assert },
    .{ "check-sat", .check_sat },
    .{ "check-sat-assuming", .check_sat_assuming },
    .{ "declare-const", .declare_const },
    .{ "declare-datatype", .declare_datatype },
    .{ "declare-datatypes", .declare_datatypes },
    .{ "declare-fun", .declare_fun },
    .{ "declare-sort", .declare_sort },
    .{ "define-fun", .define_fun },
    .{ "define-fun-rec", .define_fun_rec },
    .{ "define-funs-rec", .define_funs_rec },
    .{ "define-sort", .define_sort },
    .{ "echo", .echo },
    .{ "exit", .exit },
    .{ "get-assertions", .get_assertions },
    .{ "get-assignment", .get_assignment },
    .{ "get-info", .get_info },
    .{ "get-model", .get_model },
    .{ "get-option", .get_option },
    .{ "get-proof", .get_proof },
    .{ "get-unsat-assumptions", .get_unsat_assumptions },
    .{ "get-unsat-core", .get_unsat_core },
    .{ "get-value", .get_value },
    .{ "pop", .pop },
    .{ "push", .push },
    .{ "reset", .reset },
    .{ "reset-assertions", .reset_assertions },
    .{ "set-info", .set_info },
    .{ "set-logic", .set_logic },
    .{ "set-option", .set_option },
});

fn skip_to_level(str: []u8, start_idx: usize, start_level: usize, target_level: usize) ?usize {
    var level: usize = start_level;
    var idx = start_idx;

    var in_str: bool = false;
    var in_symb: bool = false;
    while (idx < str.len) {
        const chr = str[idx];
        switch (chr) {
            '|' => {
                if (in_str) break;
                in_symb = !in_symb;
            },
            '"' => {
                if (in_symb) break;
                in_str = !in_str;
            },
            '(' => {
                if (in_symb or in_str) break;
                level += 1;
                if (level == target_level)
                    return idx + 1;
            },
            ')' => {
                if (in_symb or in_str) break;
                // TODO: catch underflow error properly
                level -= 1;
                if (level == target_level)
                    return idx + 1;
            },
            else => {},
        }
        idx += 1;
    }
    return null;
}

const span = struct { start: usize, end: usize };
fn get_symbol(str: []u8, start_idx: usize) span {
    var idx = start_idx;

    while (idx < str.len) {
        const char = str[idx];
        if (!(char == 9 or char == 10 or char == 13 or char == 32)) {
            break;
        }
        idx += 1;
    }
    const cmd_start = idx;
    while (idx < str.len) {
        const char = str[idx];
        //TODO: incomplete for symbol
        if (!(char == '-' or
            char == '_' or
            (char >= 'a' and char <= 'z') or
            (char >= 'A' and char <= 'Z')))
            break;
        idx += 1;
    }
    return .{ .start = cmd_start, .end = idx };
}

fn print_subproblem(out: anytype, str: []u8, scopes: *std.ArrayList(Scope), command: []const u8) !void {
    for (scopes.items) |scope| {
        var i: usize = 0;
        while (i < scope.intervals.items.len) : ({
            i += 2;
        }) {
            const start = scope.intervals.items[i];
            const end = scope.intervals.items[i + 1];
            try out.print("{s}", .{str[start..end]});
        }
    }
    try out.print("{s}\n", .{command});
}

pub fn main() !u8 {
    var area = std.heap.ArenaAllocator.init(std.heap.page_allocator);
    defer area.deinit();
    const allocator = area.allocator();

    const stdout_file = std.io.getStdOut().writer();
    var bw = std.io.bufferedWriter(stdout_file);
    const stdout = bw.writer();

    if (.windows == @import("builtin").os.tag) {
        print("Windows is not supported.\n", .{});
        return 1;
    }

    if (std.os.argv.len < 2) {
        print("Klammerhammer -- Extract SMT-LIB metadata\n\n", .{});
        print("Usage:\n", .{});
        print("\tklhm FILENAME\n", .{});
        return 1;
    }

    const filename = std.mem.span(std.os.argv[1]);
    const file = try fs.cwd().openFile(filename, .{});
    defer file.close();

    const md = try file.metadata();
    const size = md.size();
    try stdout.print("File size: {}\n", .{size});
    const ptr = try std.os.mmap(
        null,
        md.size(),
        std.os.PROT.READ | std.os.PROT.WRITE,
        std.os.MAP.PRIVATE,
        file.handle,
        0,
    );
    defer std.os.munmap(ptr);

    var benchmarkData: BenchmarkData = .{};
    benchmarkData.size = size;

    var scopes = std.ArrayList(Scope).init(allocator);
    try scopes.append(Scope{ .intervals = std.ArrayList(usize).init(allocator) });
    var top = &scopes.items[scopes.items.len - 1];
    try top.intervals.append(0);

    var idx: usize = 0;
    while (idx < ptr.len) {
        idx = skip_to_level(ptr, idx, 0, 1) orelse break;
        const level_start_idx = idx - 1;

        const cmdSpan = get_symbol(ptr, idx);
        const cmdStr = ptr[cmdSpan.start..cmdSpan.end];

        if (CmdMap.get(cmdStr)) |cmd| {
            switch (cmd) {
                .set_logic => {
                    const logicSpan = get_symbol(ptr, idx);
                    benchmarkData.logic = ptr[logicSpan.start..logicSpan.end];
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
                },
                .push => {
                    // calculate end of old level
                    try top.intervals.append(level_start_idx);
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
                    try scopes.append(Scope{ .intervals = std.ArrayList(usize).init(allocator) });
                    top = &scopes.items[scopes.items.len - 1];
                    try top.intervals.append(idx);
                },
                .pop => {
                    try top.intervals.append(level_start_idx);
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
                    top.intervals.deinit();
                    _ = scopes.pop();
                    top = &scopes.items[scopes.items.len - 1];
                    try top.intervals.append(idx);
                },
                .check_sat, .check_sat_assuming => {
                    try top.intervals.append(level_start_idx);
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;

                    try stdout.print("---------\n", .{});
                    try print_subproblem(stdout, ptr, &scopes, ptr[level_start_idx..idx]);
                    try stdout.print("---------\n", .{});
                    try bw.flush();
                    benchmarkData.subbenchmarkCount += 1;

                    try top.intervals.append(idx);
                },
                .exit => {
                    break;
                },
                else => {
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
                },
            }
        } else {
            // Unkown command, do nothing
            idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
        }
    }

    benchmarkData.isIncremental = benchmarkData.subbenchmarkCount > 1;
    try stdout.print("{any}\n", .{benchmarkData});
    try bw.flush();
    return 0;
}
